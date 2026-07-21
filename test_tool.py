"""
Comprehensive MCP Tools Testing Suite

This module provides testing utilities for all Model Context Protocol (MCP) servers
configured in the project, with specific focus on HeroUI React components.

Usage:
    python test_tool.py                    # Run all tests
    python test_tool.py --heroui-only      # Run HeroUI tests only
    python test_tool.py --connection-only  # Test only server connections

Example output:
    🚀 Starting MCP Tools Test Suite
    
    ======================================================================
    Testing All MCP Server Connections
    ======================================================================
      firecrawl: ✅ Connected
      context7: ✅ Connected
      filesystem: ✅ Connected
      playwright: ✅ Connected
      heroui-react: ✅ Connected
    
    ======================================================================
    HeroUI React MCP Server - Complete Test Suite
    ======================================================================
    
    ✅ Connection established
    ✅ 5 tools discovered
    ✅ Component info test passed
    ✅ Code generation test passed
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime

from dotenv import load_dotenv

try:
    from mcp_use import MCPClient
    from mcp_tools.initialize_mcps import (
        load_mcp_server_config,
        create_mcp_client,
        run_mcp_agent,
        test_all_connections,
    )
    from agents.llm import mcp_code_llm
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MCPServerTester:
    """Base class for MCP server testing"""

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.config = load_mcp_server_config()
        self.results: Dict[str, Any] = {
            "server": server_name,
            "timestamp": datetime.now().isoformat(),
            "connection": False,
            "tools": [],
            "tests": {},
            "errors": [],
        }

    async def test_connection(self) -> bool:
        """Test connection to MCP server"""
        logger.info(f"\n🔌 Testing connection to {self.server_name}...")
        try:
            client = MCPClient(
                config=self.config,
                allowed_servers=[self.server_name],
            )
            sessions = await client.create_all_sessions()
            is_ok = bool(sessions)
            if is_ok:
                logger.info(f"✅ {self.server_name} is connected")
                self.results["connection"] = True
            else:
                logger.warning(f"⚠️  {self.server_name} - no sessions created")
            await client.close_all_sessions()
            return is_ok
        except Exception as exc:
            logger.error(f"❌ {self.server_name} connection failed: {exc}")
            self.results["errors"].append(str(exc))
            return False

    async def discover_tools(self) -> List[str]:
        """Discover all tools provided by the server"""
        logger.info(f"\n🔧 Discovering tools for {self.server_name}...")
        try:
            client = create_mcp_client([self.server_name])
            await client.create_all_sessions()
            tools = client.get_tools(self.server_name)
            tool_names = [tool.get("name", "unknown") for tool in tools]
            logger.info(f"✅ Found {len(tool_names)} tools: {', '.join(tool_names[:5])}")
            if len(tool_names) > 5:
                logger.info(f"   ... and {len(tool_names) - 5} more")
            self.results["tools"] = tool_names
            await client.close_all_sessions()
            return tool_names
        except Exception as exc:
            logger.error(f"❌ Tool discovery failed for {self.server_name}: {exc}")
            self.results["errors"].append(f"Tool discovery: {exc}")
            return []

    async def run_simple_test(
        self,
        test_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_steps: int = 5,
    ) -> bool:
        """Run a simple test prompt through the MCP agent"""
        logger.info(f"\n🧪 Running test: {test_name}")
        try:
            if system_prompt is None:
                system_prompt = f"You are an expert with {self.server_name}. Provide accurate, helpful responses."

            result = await run_mcp_agent(
                prompt=prompt,
                allowed_servers=[self.server_name],
                system_prompt=system_prompt,
                llm=mcp_code_llm(),
                max_steps=max_steps,
            )

            if result and len(result) > 20:
                logger.info(f"✅ {test_name} passed")
                logger.info(f"   Response: {result[:100]}...")
                self.results["tests"][test_name] = "pass"
                return True
            else:
                logger.warning(f"⚠️  {test_name} - empty or minimal response")
                self.results["tests"][test_name] = "minimal_response"
                return False

        except Exception as exc:
            logger.error(f"❌ {test_name} failed: {exc}")
            self.results["tests"][test_name] = f"error: {exc}"
            return False


class HeroUIReactTester(MCPServerTester):
    """Specialized tester for HeroUI React MCP server"""

    def __init__(self):
        super().__init__("heroui-react")

    async def test_component_info(self) -> bool:
        """Test retrieving component information"""
        return await self.run_simple_test(
            "get_component_info",
            "What is the Button component in HeroUI React? Provide key features and usage examples.",
            "You are a HeroUI React expert. Provide accurate information about components.",
        )

    async def test_component_list(self) -> bool:
        """Test listing all components"""
        return await self.run_simple_test(
            "list_components",
            "List all the main components available in HeroUI React with brief descriptions.",
            "You are a HeroUI documentation expert. Provide comprehensive component listings.",
        )

    async def test_styling_system(self) -> bool:
        """Test information about styling system"""
        return await self.run_simple_test(
            "styling_system",
            "How does the HeroUI React styling system work? What are the key customization options?",
            "You are a HeroUI theming expert. Explain styling and customization thoroughly.",
        )

    async def test_accessibility(self) -> bool:
        """Test accessibility features"""
        return await self.run_simple_test(
            "accessibility_features",
            "What accessibility features does HeroUI React provide? How are they implemented?",
            "You are an accessibility expert. Provide detailed accessibility information.",
        )

    async def test_code_generation(self) -> bool:
        """Test generating actual component code"""
        logger.info("\n🧪 Running test: generate_button_component")
        try:
            prompt = (
                "Generate a complete, production-ready HeroUI React Button component example. "
                "Include TypeScript types, multiple variants (solid, bordered, flat, faded, shadow, light), "
                "sizes (sm, md, lg), colors, disabled state, and loading state. "
                "Provide full working code."
            )

            result = await run_mcp_agent(
                prompt=prompt,
                allowed_servers=[self.server_name],
                system_prompt=(
                    "You are an expert React developer. Generate production-ready HeroUI component code "
                    "with proper TypeScript types and comprehensive examples."
                ),
                llm=mcp_code_llm(),
                max_steps=8,
            )

            if result and ("jsx" in result.lower() or "tsx" in result.lower()):
                logger.info("✅ generate_button_component passed")
                logger.info(f"   Generated {len(result)} characters of code")
                self.results["tests"]["generate_button_component"] = "pass"
                return True
            else:
                logger.warning("⚠️  generate_button_component - no code detected in response")
                self.results["tests"]["generate_button_component"] = "no_code_generated"
                return False

        except Exception as exc:
            logger.error(f"❌ generate_button_component failed: {exc}")
            self.results["tests"]["generate_button_component"] = f"error: {exc}"
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all HeroUI React tests"""
        logger.info("\n" + "=" * 70)
        logger.info("HeroUI React MCP Server - Complete Test Suite")
        logger.info("=" * 70)

        # Connection and discovery
        if not await self.test_connection():
            logger.error("Cannot proceed - server not accessible")
            self.print_summary()
            return self.results

        await self.discover_tools()

        # Run component-specific tests
        logger.info("\n" + "-" * 70)
        logger.info("Running HeroUI Component Tests")
        logger.info("-" * 70)

        await self.test_component_info()
        await self.test_component_list()
        await self.test_styling_system()
        await self.test_accessibility()
        await self.test_code_generation()

        self.print_summary()
        return self.results

    def print_summary(self) -> None:
        """Print test summary"""
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)

        logger.info(f"\n📊 Server: {self.results['server']}")
        logger.info(f"   Connection: {'✅ OK' if self.results['connection'] else '❌ Failed'}")
        logger.info(f"   Tools found: {len(self.results['tools'])}")

        if self.results["tools"]:
            logger.info("   Available tools:")
            for tool in self.results["tools"][:10]:
                logger.info(f"      - {tool}")
            if len(self.results["tools"]) > 10:
                logger.info(f"      ... and {len(self.results['tools']) - 10} more")

        logger.info(f"\n🧪 Test Results: {len(self.results['tests'])} tests")
        passed = 0
        for test_name, status in self.results["tests"].items():
            if status == "pass":
                logger.info(f"   ✅ {test_name}")
                passed += 1
            else:
                logger.info(f"   ❌ {test_name}: {status}")

        logger.info(f"\n📈 Success Rate: {passed}/{len(self.results['tests'])}")

        if self.results["errors"]:
            logger.info(f"\n⚠️  Errors: {len(self.results['errors'])}")
            for error in self.results["errors"][:5]:
                logger.error(f"   - {error}")
            if len(self.results["errors"]) > 5:
                logger.error(f"   ... and {len(self.results['errors']) - 5} more")

        logger.info("\n" + "=" * 70 + "\n")

    def save_results(self, filename: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"heroui_test_results_{timestamp}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to {filename}")
            return filename
        except Exception as exc:
            logger.error(f"Failed to save results: {exc}")
            return ""


async def test_all_mcp_servers() -> Dict[str, bool]:
    """Test connection to all configured MCP servers"""
    logger.info("\n" + "=" * 70)
    logger.info("Testing All MCP Server Connections")
    logger.info("=" * 70)

    results = await test_all_connections()

    for server_name, is_connected in results.items():
        status = "✅ Connected" if is_connected else "❌ Failed"
        logger.info(f"  {server_name}: {status}")

    logger.info("=" * 70 + "\n")
    return results


async def main() -> None:
    """Main test runner"""
    logger.info("\n🚀 Starting MCP Tools Test Suite\n")

    # Parse command line arguments
    connection_only = "--connection-only" in sys.argv
    heroui_only = "--heroui-only" in sys.argv

    # Test all MCP server connections (unless heroui-only)
    if not heroui_only:
        await test_all_mcp_servers()

    # If connection-only, stop here
    if connection_only:
        logger.info("✅ Connection tests completed!")
        return

    # Run comprehensive HeroUI React tests
    heroui_tester = HeroUIReactTester()
    await heroui_tester.run_all_tests()

    # Save results
    heroui_tester.save_results()

    logger.info("\n✅ All tests completed!\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
