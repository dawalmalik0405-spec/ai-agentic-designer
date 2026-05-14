"""
Research Agent
--------------
Scrapes design inspiration from UI patterns and fetches up-to-date animation documentation.
Uses real MCP tools via centralized MCPManager.
Uses NVIDIA NIM LLM for smart filtering and summarization of scraped patterns.
"""

import asyncio
import logging
from typing import Dict, List, Any

from mcp_tools.initialize_mcps import get_tools_for_agent
from agents.llm import invoke_text_model

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Agent responsible for collecting design inspiration and documenting animation primitives."""

    def __init__(self):
        self._tools_loaded = False
        self.firecrawl_tool = None
        self.context7_tool = None

    async def _ensure_tools(self):
        if not self._tools_loaded:
            tools = await get_tools_for_agent("research")
            for t in tools:
                if "firecrawl" in t.name.lower():
                    self.firecrawl_tool = t
                if "context7" in t.name.lower():
                    self.context7_tool = t
            self._tools_loaded = True

    async def _scrape_patterns(self, keyword: str) -> List[str]:
        await self._ensure_tools()
        try:
            # Use Firecrawl tool via ainvoke
            result = await self.firecrawl_tool.ainvoke({
                "url": f"https://awwwards.com/search?q={keyword}",
                "limit": 10
            })
            # Adapt result: might be dict or ToolMessage
            if isinstance(result, dict):
                return result.get("patterns", [])
            else:
                # assume content attribute
                content = getattr(result, "content", None)
                if content:
                    import json
                    try:
                        data = json.loads(content)
                        return data.get("patterns", [])
                    except Exception:
                        return []
        except Exception as exc:
            logger.error(f"Firecrawl scrape failed for keyword '{keyword}': {exc}")
        return []

    async def _fetch_library_docs(self, lib_name: str, query: str) -> List[str]:
        await self._ensure_tools()
        try:
            resp = await self.context7_tool.ainvoke({
                "query": query,
                "libraries": [lib_name]
            })
            if isinstance(resp, dict):
                return resp.get("results", [])
            else:
                content = getattr(resp, "content", None)
                if content:
                    import json
                    try:
                        data = json.loads(content)
                        return data.get("results", [])
                    except Exception:
                        return []
        except Exception as exc:
            logger.error(f"Context7 lookup failed for lib {lib_name}: {exc}")
        return []

    async def _summarize_with_llm(self, keyword: str, animation_goal: str, patterns: List[str], docs: List[str]) -> str:
        """Use NVIDIA NIM LLM to filter and summarize scraped patterns."""
        patterns_text = "\n".join(patterns[:10])  # Limit to avoid token overflow
        docs_text = "\n".join(docs[:5])

        prompt = f"""
You are a UI research assistant. Given these scraped UI patterns and documentation snippets for {keyword} style with {animation_goal} animation:

UI PATTERNS:
{patterns_text}

DOCUMENTATION SNIPPETS:
{docs_text}

TASK:
1. Filter out irrelevant patterns (keep only those relevant to {keyword} style and {animation_goal} animation)
2. Summarize the key design elements (colors, shapes, motion types)
3. Extract actionable insights for a designer (what works, what doesn't)
4. Return a concise summary (max 300 words) with key takeaways.

Return ONLY the summary text, no JSON, no markdown fences.
"""
        try:
            summary = invoke_text_model(prompt, model_name="qwen/qwen3-next-80b-a3b-instruct", temperature=0.7)
            return summary.strip()
        except Exception as exc:
            logger.error(f"LLM summarization failed: {exc}")
            return f"Summary unavailable due to error: {exc}"

    async def gather_inspiration(
        self, keyword: str, animation_goal: str
    ) -> Dict[str, Any]:
        """
        High-level public entry point used by the Orchestrator.
        Returns a ``inspiration_data`` dict.
        """
        keyword = keyword.lower()
        animation_goal = animation_goal.lower()

        # Scrape visual patterns
        patterns = await self._scrape_patterns(keyword)

        # Choose relevant animation library
        lib_map = {
            "liquid": "GSAP",
            "3d": "Three.js",
            "glow": "Three.js",
            "spring": "React Spring",
            "physics": "React Spring",
        }
        lib_name = lib_map.get(animation_goal, "Three.js")

        # Pull newest library docs
        lib_snippets = await self._fetch_library_docs(lib_name, animation_goal)

        # Use LLM to summarize and filter the scraped data
        summary = await self._summarize_with_llm(keyword, animation_goal, patterns, lib_snippets)

        inspiration = {
            "ui_patterns": patterns,
            "animation_docs": lib_snippets,
            "inspiration_summary": summary,
            "request": f"Create a premium {keyword} design system with an animation: {animation_goal}",
        }
        return inspiration
