"""
Test suite for HeroUI React MCP tools

This module provides comprehensive testing for the HeroUI React MCP server,
including tool discovery, validation, and execution tests.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from mcp_use import MCPClient
from mcp_tools.initialize_mcps import (
    load_mcp_server_config,
    create_mcp_client,
    run_mcp_agent,
)
from agents.llm import mcp_code_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HeroUIToolsTester:
    """Test suite for HeroUI React MCP server tools"""

    def __init__(self):
        self.config = load_mcp_server_config()
        self.server_name = "heroui-react"
        self.results = {
            "connection": False,
            "tools_discovered": [],
            "tools_tested": {},
            "errors": [],
        }

    async def test_connection(self) -> bool:
        """Test basic connection to HeroUI React MCP server"""
        logger.info("=" * 60)
        logger.info("Testing HeroUI React MCP Connection")
        logger.info("=" * 60)

        try:
            client = MCPClient(
                config=self.config,
                allowed_servers=[self.server_name],
            )
            sessions = await client.create_all_sessions()
            is_connected = bool(sessions)

            if is_connected:
                logger.info("✅ Successfully connected to HeroUI React MCP server")
                self.results["connection"] = True
                await client.close_all_sessions()
                return True
            else:
                error_msg = "No sessions created"
                logger.error(f"❌ Connection failed: {error_msg}")
                self.results["errors"].append(error_msg)
                return False

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error(f"❌ Connection failed: {error_msg}")
            self.results["errors"].append(error_msg)
            return False

    async def discover_tools(self) -> list[dict[str, Any]]:
        """Discover all available tools in HeroUI React MCP"""
        logger.info("\n" + "=" * 60)
        logger.info("Discovering HeroUI React Tools")
        logger.info("=" * 60)

        try:
            client = create_mcp_client([self.server_name])
            await client.create_all_sessions()

            # Get available tools
            tools = client.get_tools(self.server_name)

            if tools:
                logger.info(f"✅ Found {len(tools)} tools:")
                for i, tool in enumerate(tools, 1):
                    tool_name = tool.get("name", "unknown")
                    tool_desc = tool.get("description", "No description")
                    logger.info(f"   {i}. {tool_name}: {tool_desc[:60]}...")
                    self.results["tools_discovered"].append(tool_name)
            else:
                logger.warning("⚠️  No tools found in HeroUI React MCP")
                self.results["tools_discovered"] = []

            await client.close_all_sessions()
            return tools or []

        except Exception as exc:
            error_msg = f"Tool discovery failed: {type(exc).__name__}: {exc}"
            logger.error(f"❌ {error_msg}")
            self.results["errors"].append(error_msg)
            return []

    async def test_tool_execution(self) -> dict[str, bool]:
        """Test execution of specific HeroUI tools"""
        logger.info("\n" + "=" * 60)
        logger.info("Testing Tool Execution")
        logger.info("=" * 60)

        test_cases = [
            {
                "name": "get_component_info",
                "prompt": "Get information about the Button component in HeroUI React",
                "expected_keywords": ["button", "component"],
            },
            {
                "name": "list_components",
                "prompt": "List all available components in HeroUI React",
                "expected_keywords": ["component", "list"],
            },
            {
                "name": "get_documentation",
                "prompt": "Get the documentation for HeroUI React components",
                "expected_keywords": ["documentation", "guide"],
            },
        ]

        results: dict[str, bool] = {}
        llm = mcp_code_llm()

        for test_case in test_cases:
            test_name = test_case["name"]
            prompt = test_case["prompt"]

            logger.info(f"\n📝 Testing: {test_name}")
            logger.info(f"   Prompt: {prompt}")

            try:
                result = await run_mcp_agent(
                    prompt=prompt,
                    allowed_servers=[self.server_name],
                    system_prompt=(
                        "You are a HeroUI React component expert. "
                        "Use the available tools to provide accurate information about HeroUI components. "
                        "Return the information in a clear, structured format."
                    ),
                    llm=llm,
                    max_steps=5,
                )

                # Check if result contains expected keywords
                result_lower = result.lower() if result else ""
                has_keywords = any(
                    keyword in result_lower
                    for keyword in test_case["expected_keywords"]
                )

                if result and has_keywords:
                    logger.info(f"✅ {test_name} succeeded")
                    logger.info(f"   Response preview: {result[:100]}...")
                    results[test_name] = True
                    self.results["tools_tested"][test_name] = "success"
                else:
                    logger.warning(f"⚠️  {test_name} returned unexpected result")
                    logger.info(f"   Response: {result[:100] if result else 'None'}...")
                    results[test_name] = False
                    self.results["tools_tested"][test_name] = "unexpected_result"

            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                logger.error(f"❌ {test_name} failed: {error_msg}")
                self.results["errors"].append(error_msg)
                self.results["tools_tested"][test_name] = "error"
                results[test_name] = False

        return results

    async def test_component_generation(self) -> bool:
        """Test generating actual HeroUI component code"""
        logger.info("\n" + "=" * 60)
        logger.info("Testing Component Code Generation")
        logger.info("=" * 60)

        prompt = (
            "Using HeroUI React, generate a complete Button component example "
            "with proper TypeScript types and styling. "
            "Include example usage with multiple variants."
        )

        logger.info(f"📝 Prompt: {prompt}")

        try:
            llm = mcp_code_llm()
            result = await run_mcp_agent(
                prompt=prompt,
                allowed_servers=[self.server_name],
                system_prompt=(
                    "You are an expert React developer with deep knowledge of HeroUI. "
                    "Generate production-ready component examples with proper types and documentation."
                ),
                llm=llm,
                max_steps=8,
            )

            if result and "button" in result.lower() and ("jsx" in result.lower() or "tsx" in result.lower()):
                logger.info("✅ Component generation succeeded")
                logger.info(f"   Generated code preview: {result[:150]}...")
                self.results["tools_tested"]["component_generation"] = "success"
                return True
            else:
                logger.warning("⚠️  Component generation returned unexpected result")
                self.results["tools_tested"]["component_generation"] = "unexpected_result"
                return False

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error(f"❌ Component generation failed: {error_msg}")
            self.results["errors"].append(error_msg)
            self.results["tools_tested"]["component_generation"] = "error"
            return False

    async def test_documentation_retrieval(self) -> bool:
        """Test retrieving HeroUI documentation"""
        logger.info("\n" + "=" * 60)
        logger.info("Testing Documentation Retrieval")
        logger.info("=" * 60)

        prompt = (
            "What are the main features and benefits of using HeroUI React? "
            "Provide a summary of its key components and styling system."
        )

        logger.info(f"📝 Prompt: {prompt}")

        try:
            llm = mcp_code_llm()
            result = await run_mcp_agent(
                prompt=prompt,
                allowed_servers=[self.server_name],
                system_prompt=(
                    "You are a HeroUI documentation expert. "
                    "Provide clear, accurate information about HeroUI React features and components."
                ),
                llm=llm,
                max_steps=5,
            )

            if result and len(result) > 50:
                logger.info("✅ Documentation retrieval succeeded")
                logger.info(f"   Retrieved info: {result[:150]}...")
                self.results["tools_tested"]["documentation_retrieval"] = "success"
                return True
            else:
                logger.warning("⚠️  Documentation retrieval returned minimal result")
                self.results["tools_tested"]["documentation_retrieval"] = "minimal_result"
                return False

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error(f"❌ Documentation retrieval failed: {error_msg}")
            self.results["errors"].append(error_msg)
            self.results["tools_tested"]["documentation_retrieval"] = "error"
            return False

    def print_summary(self) -> None:
        """Print summary of all test results"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)

        logger.info(f"\n📊 Connection Status: {'✅ Connected' if self.results['connection'] else '❌ Failed'}")

        logger.info(f"\n🔧 Tools Discovered: {len(self.results['tools_discovered'])}")
        if self.results["tools_discovered"]:
            for tool in self.results["tools_discovered"]:
                logger.info(f"   - {tool}")

        logger.info(f"\n🧪 Tool Tests: {len(self.results['tools_tested'])}")
        for tool_name, status in self.results["tools_tested"].items():
            status_icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️ "
            logger.info(f"   {status_icon} {tool_name}: {status}")

        if self.results["errors"]:
            logger.info(f"\n⚠️  Errors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                logger.error(f"   - {error}")

        success_count = sum(
            1
            for status in self.results["tools_tested"].values()
            if status == "success"
        )
        total_tests = len(self.results["tools_tested"])

        logger.info(f"\n📈 Overall Success Rate: {success_count}/{total_tests}")
        logger.info("=" * 60)

        # Save results to file
        self.save_results()

    def save_results(self) -> None:
        """Save test results to JSON file"""
        output_file = "heroui_test_results.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"\n💾 Results saved to {output_file}")
        except Exception as exc:
            logger.error(f"Failed to save results: {exc}")


async def main() -> None:
    """Main test runner"""
    logger.info("\n🚀 Starting HeroUI React MCP Tools Test Suite\n")

    tester = HeroUIToolsTester()

    # Run tests
    connection_ok = await tester.test_connection()

    if not connection_ok:
        logger.error("\n❌ Cannot proceed - HeroUI React MCP server not accessible")
        tester.print_summary()
        return

    await tester.discover_tools()
    await tester.test_tool_execution()
    await tester.test_component_generation()
    await tester.test_documentation_retrieval()

    tester.print_summary()

    logger.info("\n✅ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
