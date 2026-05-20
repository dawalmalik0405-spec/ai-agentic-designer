"""
MCP Server Initialization for LangChain Agents
===========================================
Uses langchain-mcp-adapters for clean MCP-to-LangChain tool conversion.
All agents get real, connected MCP tools via this manager.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
from langchain_mcp_adapters.sessions import StdioConnection
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import StructuredTool

CURRENT_DIR = os.path.dirname(__file__)
PACKAGE_ROOT = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PACKAGE_ROOT, ".env"), override=False)
load_dotenv()


class MCPServerStdio:
    """Compatibility shim for the old MCPServerStdio API."""

    def __init__(self, command: str, args: list[str], env: dict | None = None):
        self.config: StdioConnection = {
            "transport": "stdio",
            "command": command,
            "args": args,
            "env": env or {},
        }

    async def get_tools(self) -> list:
        return await load_mcp_tools(session=None, connection=self.config)


MCPConfig = dict  # placeholder, not used directly

logger = logging.getLogger(__name__)

RESEARCH_DOC_TOOL_NAMES = {"resolve-library-id", "query-docs"}
FILESYSTEM_TOOL_NAMES = {
    "read_file",
    "read_text_file",
    "read_media_file",
    "read_multiple_files",
    "write_file",
    "edit_file",
    "create_directory",
    "list_directory",
    "list_directory_with_sizes",
    "directory_tree",
    "move_file",
    "search_files",
    "get_file_info",
    "list_allowed_directories",
}
BROWSER_TOOL_PREFIX = "browser_"


def _filesystem_allowed_directories() -> list[str]:
    candidates = [
        os.getenv("MCP_FILESYSTEM_ROOT"),
        PROJECT_ROOT,
        PACKAGE_ROOT,
    ]
    normalized: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        if not candidate:
            continue
        path = os.path.abspath(candidate)
        if path in seen or not os.path.isdir(path):
            continue
        seen.add(path)
        normalized.append(path)

    return normalized


class MCPManager:
    """Manages connections to all MCP servers and exposes tools to agents."""

    def __init__(self):
        self.servers = {}
        self._initialized = False
        self._tool_cache = {}
        self._all_tools: Optional[List[StructuredTool]] = None

    async def initialize_servers(self):
        """Initialize all MCP server connections."""
        if self._initialized:
            return

        # Firecrawl MCP - for web scraping UI patterns
        self.servers["firecrawl"] = MCPServerStdio(
            command="npx",
            args=["-y", "firecrawl-mcp@latest"],
            env={
                "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", ""),
                "NODE_ENV": "production"
            }
        )

        # Context7 MCP - for documentation lookup
        self.servers["context7"] = MCPServerStdio(
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"],
            env={}
        )

        # Filesystem MCP - for file operations
        filesystem_roots = _filesystem_allowed_directories()
        self.servers["filesystem"] = MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", *filesystem_roots],
            env={}
        )

        # Playwright MCP - for browser testing
        self.servers["playwright"] = MCPServerStdio(
            command="npx",
            args=["-y", "@playwright/mcp@latest"],
            env={}
        )

        self._initialized = True
        logger.info("All MCP servers configured via langchain-mcp-adapters")

    async def get_tools_for_agent(self, agent_type: str) -> List[StructuredTool]:
        """Get MCP tools filtered by agent type.

        Args:
            agent_type: One of 'design', 'research', 'review', 'code', 'all'

        Returns:
            List of StructuredTool instances for that agent.
        """
        await self.initialize_servers()

        # Return cached tools if available
        if agent_type in self._tool_cache:
            return self._tool_cache[agent_type]

        all_tools = await self._load_all_tools()

        if agent_type == "design":
            filtered = [
                t for t in all_tools
                if t.name in RESEARCH_DOC_TOOL_NAMES or t.name in FILESYSTEM_TOOL_NAMES
            ]
        elif agent_type == "research":
            filtered = [
                t for t in all_tools
                if t.name.startswith("firecrawl_") or t.name in RESEARCH_DOC_TOOL_NAMES
            ]
        elif agent_type == "review":
            filtered = [t for t in all_tools if t.name.startswith(BROWSER_TOOL_PREFIX)]
        elif agent_type == "code":
            filtered = [
                t for t in all_tools
                if t.name in RESEARCH_DOC_TOOL_NAMES or t.name in FILESYSTEM_TOOL_NAMES
            ]
        else:
            filtered = all_tools

        self._tool_cache[agent_type] = filtered
        logger.info(f"Returning {len(filtered)} tools for agent type '{agent_type}'")
        return filtered

    async def _load_all_tools(self) -> List[StructuredTool]:
        if self._all_tools is not None:
            return self._all_tools

        all_tools: List[StructuredTool] = []
        had_failures = False
        for server_name, server in self.servers.items():
            try:
                tools = await server.get_tools()
                all_tools.extend(tools)
                logger.info(f"Loaded {len(tools)} tools from {server_name}")
            except Exception as exc:
                had_failures = True
                logger.error(f"Failed to load tools from {server_name}: {exc}")

        if not had_failures:
            self._all_tools = all_tools
        return all_tools

    async def test_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all MCP servers."""
        results = {}
        await self.initialize_servers()

        for name, server in self.servers.items():
            try:
                tools = await server.get_tools()
                results[name] = len(tools) > 0
                logger.info(f"✓ {name}: {len(tools)} tools available")
            except Exception as exc:
                results[name] = False
                logger.error(f"✗ {name}: connection failed - {exc}")

        return results


# Global singleton
_manager: Optional[MCPManager] = None


async def get_mcp_manager() -> MCPManager:
    """Get or create the global MCPManager instance."""
    global _manager
    if _manager is None:
        _manager = MCPManager()
        await _manager.initialize_servers()
    return _manager


async def get_tools_for_agent(agent_type: str) -> List[StructuredTool]:
    """Convenience function to get tools for an agent type."""
    manager = await get_mcp_manager()
    return await manager.get_tools_for_agent(agent_type)


async def test_all_connections() -> Dict[str, bool]:
    """Test all MCP server connections."""
    manager = await get_mcp_manager()
    return await manager.test_connectivity()
