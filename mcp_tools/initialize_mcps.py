"""
MCP pipeline helpers built on mcp-use.

Agents create an MCPClient from the shared servers.json config, restrict it to
the servers they need, and let MCPAgent decide when to call tools.
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp_use import MCPAgent, MCPClient, session

from agents.llm import (CODE_MODEL, deepseek_llm, qwen_llm)

CURRENT_DIR = os.path.dirname(__file__)
PACKAGE_ROOT = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_ROOT)
DEFAULT_SERVERS_PATH = os.path.join(CURRENT_DIR, "servers.json")

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PACKAGE_ROOT, ".env"), override=False)
load_dotenv()

logger = logging.getLogger(__name__)


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


def _expand_config_value(value: Any) -> Any:
    if isinstance(value, str):
        if value == "${MCP_FILESYSTEM_ROOTS}":
            return _filesystem_allowed_directories()

        if value.startswith("${") and value.endswith("}"):
            return os.getenv(value[2:-1], "")

        return value

    if isinstance(value, list):
        expanded: list[Any] = []
        for item in value:
            resolved = _expand_config_value(item)
            if isinstance(resolved, list):
                expanded.extend(resolved)
            elif resolved not in (None, ""):
                expanded.append(resolved)
        return expanded

    if isinstance(value, dict):
        expanded: dict[str, Any] = {}
        for key, item in value.items():
            resolved = _expand_config_value(item)
            if resolved not in (None, ""):
                expanded[key] = resolved
        return expanded

    return value


def load_mcp_server_config() -> dict[str, Any]:
    config_path = os.getenv("MCP_CONFIG_PATH", DEFAULT_SERVERS_PATH)
    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config, dict) or not isinstance(config.get("mcpServers"), dict):
        raise ValueError(f"MCP config must contain an mcpServers object: {config_path}")

    return _expand_config_value(config)


def create_mcp_client(allowed_servers: list[str]) -> MCPClient:
    return MCPClient(
        config=load_mcp_server_config(),
        allowed_servers=allowed_servers,
    )


async def run_mcp_agent(
    prompt: str,
    *,
    allowed_servers: list[str],
    system_prompt: str,
    disallowed_tools: list[str] | None = None,
    model_name: str = CODE_MODEL,
    temperature: float = 0.2,
    max_steps: int = 12,
) -> str:
    client = create_mcp_client(allowed_servers=allowed_servers)
    llm = model_name
    agent = MCPAgent(
        llm=llm,
        client=client,
        system_prompt=system_prompt,
        disallowed_tools=disallowed_tools,
        max_steps=max_steps,
    )
    result = await agent.run(prompt)
    return str(result).strip()


async def test_all_connections() -> dict[str, bool]:
    config = load_mcp_server_config()
    results: dict[str, bool] = {}

    for server_name in config.get("mcpServers", {}):
        client = MCPClient(config=config, allowed_servers=[server_name])
        try:
            sessions = await client.create_all_sessions()
            results[server_name] = bool(sessions)
            await client.close_all_sessions()
        except Exception as exc:
            logger.error("MCP server connection failed for %s: %s", server_name, exc)
            results[server_name] = False

    return results



async def inspect_tools():

    client = create_mcp_client(
        allowed_servers=["firecrawl"]
    )

    sessions = await client.create_all_sessions()

    for name, session in sessions.items():

        print(f"\nSERVER: {name}")

        tools = await session.list_tools()

        for tool in tools:

            for tool in tools:
                if tool.name == "firecrawl_agent":
                    print(tool.inputSchema)


if __name__ == "__main__":
    import asyncio

    asyncio.run(inspect_tools())