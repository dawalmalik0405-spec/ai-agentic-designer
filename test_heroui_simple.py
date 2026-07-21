"""
Simple HeroUI React MCP Test

A minimal, focused test for HeroUI React MCP server.
Run: python test_heroui_simple.py

Output: Console logs + JSON results file
"""

import asyncio
import json
import logging
from datetime import datetime

from mcp_use import MCPClient
from mcp_tools.initialize_mcps import load_mcp_server_config, run_mcp_agent
from agents.llm import mcp_code_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_heroui_mcp():
    """Simple HeroUI MCP test"""
    logger.info("\n🚀 Testing HeroUI React MCP\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
    }
    
    try:
        # Test 1: Connection
        logger.info("1️⃣  Testing connection...")
        config = load_mcp_server_config()
        client = MCPClient(config=config, allowed_servers=["heroui-react"])
        sessions = await client.create_all_sessions()
        
        if sessions:
            logger.info("✅ Connected to HeroUI React MCP\n")
            results["tests"]["connection"] = "pass"
        else:
            logger.error("❌ Connection failed\n")
            results["tests"]["connection"] = "fail"
            return results
        
        # Test 2: Tool Discovery
        logger.info("2️⃣  Discovering tools...")
        tools = client.get_tools("heroui-react")
        tool_names = [t.get("name", "unknown") for t in tools]
        logger.info(f"✅ Found {len(tool_names)} tools: {', '.join(tool_names[:3])}\n")
        results["tests"]["tool_discovery"] = "pass"
        results["tools_count"] = len(tool_names)
        
        await client.close_all_sessions()
        
        # Test 3: Component Info
        logger.info("3️⃣  Getting component information...")
        response = await run_mcp_agent(
            prompt="What is the Button component in HeroUI React?",
            allowed_servers=["heroui-react"],
            system_prompt="You are a HeroUI expert. Provide info about the Button component.",
            llm=mcp_code_llm(),
            max_steps=5,
        )
        
        if response and "button" in response.lower():
            logger.info("✅ Got component info\n")
            results["tests"]["component_info"] = "pass"
        else:
            logger.warning("⚠️  Unexpected response\n")
            results["tests"]["component_info"] = "partial"
        
        # Test 4: Code Generation
        logger.info("4️⃣  Generating component code...")
        code_response = await run_mcp_agent(
            prompt="Generate a simple HeroUI Button component with TypeScript types.",
            allowed_servers=["heroui-react"],
            system_prompt="You are a React expert. Generate production-ready HeroUI code.",
            llm=mcp_code_llm(),
            max_steps=8,
        )
        
        if code_response and ("jsx" in code_response.lower() or "tsx" in code_response.lower()):
            logger.info("✅ Generated component code\n")
            results["tests"]["code_generation"] = "pass"
        else:
            logger.warning("⚠️  No code generated\n")
            results["tests"]["code_generation"] = "partial"
        
        # Summary
        logger.info("=" * 50)
        passed = sum(1 for v in results["tests"].values() if v == "pass")
        total = len(results["tests"])
        logger.info(f"Results: {passed}/{total} tests passed ✅\n")
        results["success_rate"] = f"{passed}/{total}"
        
    except Exception as exc:
        logger.error(f"❌ Error: {exc}\n")
        results["error"] = str(exc)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"heroui_simple_results_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"💾 Results saved to {filename}\n")
    return results


if __name__ == "__main__":
    asyncio.run(test_heroui_mcp())
