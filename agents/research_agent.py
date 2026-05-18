"""
Research Agent
--------------
Scrapes design inspiration from UI patterns and fetches up-to-date animation documentation.
Uses real MCP tools via centralized MCPManager.
Uses NVIDIA NIM LLM for smart filtering and summarization of scraped patterns.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any

from mcp_tools.initialize_mcps import get_tools_for_agent
from agents.llm import invoke_text_model

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Agent responsible for collecting design inspiration and documenting animation primitives."""

    def __init__(self):
        self._tools_loaded = False
        self.firecrawl_search_tool = None
        self.resolve_library_tool = None
        self.query_docs_tool = None

    @staticmethod
    def _extract_payload(result: Any) -> Any:
        if isinstance(result, dict):
            return result

        content = getattr(result, "content", None)
        if isinstance(content, list):
            joined = "\n".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
            content = joined

        if isinstance(content, str):
            try:
                return json.loads(content)
            except Exception:
                return content

        return result

    @staticmethod
    def _extract_context7_library_id(payload: Any) -> str | None:
        candidates: list[str] = []

        if isinstance(payload, str):
            candidates.append(payload)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and "text" in item:
                    candidates.append(str(item["text"]))
                elif item:
                    candidates.append(str(item))
        elif isinstance(payload, dict):
            for key in ("text", "content", "results", "data"):
                value = payload.get(key)
                if isinstance(value, str):
                    candidates.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and "text" in item:
                            candidates.append(str(item["text"]))
                        elif item:
                            candidates.append(str(item))

        for candidate in candidates:
            match = re.search(r"Context7-compatible library ID:\s*(/[^\s]+)", candidate)
            if match:
                return match.group(1)

        return None

    async def _ensure_tools(self):
        if not self._tools_loaded:
            tools = await get_tools_for_agent("research")
            for t in tools:
                if t.name == "firecrawl_search":
                    self.firecrawl_search_tool = t
                elif t.name == "resolve-library-id":
                    self.resolve_library_tool = t
                elif t.name == "query-docs":
                    self.query_docs_tool = t
            self._tools_loaded = True

    @staticmethod
    def _build_research_query(keyword: str, animation_goal: str) -> str:
        style = str(keyword or "").strip().lower()
        request = re.sub(r"\s+", " ", str(animation_goal or "").strip())
        request = request[:180]

        style_modifiers = {
            "minimalism": "minimalist editorial website ui inspiration",
            "glassmorphism": "glassmorphism landing page ui inspiration",
            "skeuomorphism": "skeuomorphic interface ui inspiration",
            "claymorphism": "claymorphism 3d soft ui inspiration",
            "liquid_glass": "liquid glass premium interface inspiration",
            "neo_brutalism": "neo brutalist website ui inspiration",
        }

        style_phrase = style_modifiers.get(style, f"{style} website ui inspiration")

        if request:
            return f"{request} {style_phrase}"
        return style_phrase

    async def _scrape_patterns(self, keyword: str) -> List[str]:
        await self._ensure_tools()
        if not self.firecrawl_search_tool:
            logger.error("Firecrawl search tool is unavailable")
            return []

        try:
            result = await self.firecrawl_search_tool.ainvoke({
                "query": f"{keyword} website design inspiration",
                "limit": 5,
                "sources": [{"type": "web"}],
            })
            payload = self._extract_payload(result)
            if isinstance(payload, dict):
                candidates = payload.get("data") or payload.get("results") or []
            elif isinstance(payload, list):
                candidates = payload
            else:
                candidates = [payload] if payload else []

            normalized: List[str] = []
            for item in candidates:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("metadata", {}).get("title") or ""
                    url = item.get("url") or item.get("sourceURL") or ""
                    snippet = item.get("description") or item.get("markdown") or item.get("content") or ""
                    text = " | ".join(part for part in [title, snippet, url] if part)
                    if text:
                        normalized.append(text)
                elif item:
                    normalized.append(str(item))
            return normalized
        except Exception as exc:
            logger.error(f"Firecrawl scrape failed for keyword '{keyword}': {exc}")
        return []

    async def _scrape_patterns_for_request(self, keyword: str, animation_goal: str) -> List[str]:
        query = self._build_research_query(keyword=keyword, animation_goal=animation_goal)
        logger.info("Research query: %s", query)

        await self._ensure_tools()
        if not self.firecrawl_search_tool:
            logger.error("Firecrawl search tool is unavailable")
            return []

        try:
            result = await self.firecrawl_search_tool.ainvoke({
                "query": query,
                "limit": 8,
                "sources": [{"type": "web"}, {"type": "images"}],
            })
            payload = self._extract_payload(result)
            if isinstance(payload, dict):
                candidates = payload.get("data") or payload.get("results") or []
            elif isinstance(payload, list):
                candidates = payload
            else:
                candidates = [payload] if payload else []

            normalized: List[str] = []
            for item in candidates:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("metadata", {}).get("title") or ""
                    url = item.get("url") or item.get("sourceURL") or ""
                    snippet = item.get("description") or item.get("markdown") or item.get("content") or ""
                    text = " | ".join(part for part in [title, snippet, url] if part)
                    if text:
                        normalized.append(text)
                elif item:
                    normalized.append(str(item))
            return normalized
        except Exception as exc:
            logger.error("Firecrawl scrape failed for query '%s': %s", query, exc)
            return []

    async def _fetch_library_docs(self, lib_name: str, query: str) -> List[str]:
        await self._ensure_tools()
        if not self.resolve_library_tool or not self.query_docs_tool:
            logger.error("Context7 tools are unavailable")
            return []

        try:
            resolved = await self.resolve_library_tool.ainvoke({
                "query": query,
                "libraryName": lib_name,
            })
            resolved_payload = self._extract_payload(resolved)
            library_id = self._extract_context7_library_id(resolved_payload)

            if not library_id:
                logger.error("Context7 failed to resolve library id for %s", lib_name)
                return []

            resp = await self.query_docs_tool.ainvoke({
                "libraryId": library_id,
                "query": query,
            })
            payload = self._extract_payload(resp)
            if isinstance(payload, dict):
                results = payload.get("results") or payload.get("snippets") or payload.get("data") or []
            elif isinstance(payload, list):
                results = payload
            else:
                results = [payload] if payload else []

            return [json.dumps(item) if isinstance(item, dict) else str(item) for item in results]
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

        # Scrape visual patterns using both design style and product/domain context.
        patterns = await self._scrape_patterns_for_request(keyword, animation_goal)

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
