import json
import logging
import os
import re
from typing import Any

try:
    from .llm import CODE_MODEL, invoke_text_model
    from ..mcp_tools.initialize_mcps import get_tools_for_agent
except ImportError:
    from agents.llm import CODE_MODEL, invoke_text_model
    from mcp_tools.initialize_mcps import get_tools_for_agent

logger = logging.getLogger(__name__)
RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", CODE_MODEL)
RESEARCH_QUERY_SYSTEM_PROMPT = """
You are a senior design research strategist.

Generate concise web-search queries for UI inspiration research.

Rules:
- Return valid JSON only
- Return an object with a single key: "queries"
- "queries" must be an array of 2 to 3 search strings
- Queries should combine product/domain intent, visual style, and UI inspiration language
- Prefer queries that are likely to return high-quality modern website references
- Do not include markdown
"""

RESEARCH_SUMMARY_SYSTEM_PROMPT = """
You are a senior UI research analyst.

Summarize website inspiration results into short, high-signal design guidance.

Rules:
- Focus on layout patterns, visual language, motion cues, and quality signals
- Be concrete, not generic
- Do not mention missing data unless results are actually empty
- Return plain text only
- Keep the response under 140 words
"""

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class ResearchAgent:
    def __init__(self):
        self._tools_loaded = False
        self.firecrawl_search_tool = None

    async def _ensure_tools(self) -> None:
        if self._tools_loaded:
            return

        tools = await get_tools_for_agent("research")
        logger.info("Research agent loaded %s tools", len(tools))
        for tool in tools:
            if tool.name == "firecrawl_search":
                self.firecrawl_search_tool = tool
                break

        self._tools_loaded = True
        logger.info(
            "Research firecrawl_search tool available: %s",
            bool(self.firecrawl_search_tool),
        )

    @staticmethod
    def _extract_payload(result: Any) -> Any:
        if isinstance(result, dict):
            return result

        if isinstance(result, list):
            extracted_items: list[Any] = []
            for item in result:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    if text:
                        try:
                            extracted_items.append(json.loads(text))
                            continue
                        except Exception:
                            extracted_items.append(text)
                            continue
                extracted_items.append(item)

            if len(extracted_items) == 1:
                return extracted_items[0]
            return extracted_items

        content = getattr(result, "content", None)
        if isinstance(content, list):
            extracted_items: list[Any] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    if text:
                        try:
                            extracted_items.append(json.loads(text))
                            continue
                        except Exception:
                            extracted_items.append(text)
                            continue
                extracted_items.append(item)

            if len(extracted_items) == 1:
                return extracted_items[0]
            return extracted_items

        if isinstance(content, str):
            try:
                return json.loads(content)
            except Exception:
                return content

        return result

    @staticmethod
    def _extract_candidates(payload: Any) -> list[Any]:
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), dict):
                data = payload["data"]
                web_items = data.get("web") or []
                image_items = data.get("images") or []
                combined = []
                if isinstance(web_items, list):
                    combined.extend(web_items)
                if isinstance(image_items, list):
                    combined.extend(image_items)
                if combined:
                    return combined

            data_items = payload.get("data")
            if isinstance(data_items, list):
                return data_items

            result_items = payload.get("results")
            if isinstance(result_items, list):
                return result_items

            return [payload]

        if isinstance(payload, list):
            return payload

        return [payload] if payload else []

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @staticmethod
    def _style_phrase(selected_style: str) -> str:
        style_map = {
            "minimalism": "minimal editorial interface",
            "glassmorphism": "glassmorphism premium interface",
            "skeuomorphism": "skeuomorphic tactile interface",
            "claymorphism": "claymorphism soft 3d interface",
            "liquid_glass": "liquid glass futuristic interface",
            "neo_brutalism": "neo brutalist bold interface",
        }
        return style_map.get(selected_style, selected_style.replace("_", " "))

    def _build_queries_fallback(
        self,
        prompt: str,
        selected_style: str,
        pages: list[dict[str, Any]],
    ) -> list[str]:
        prompt_text = self._normalize_text(prompt)[:160]
        style_phrase = self._style_phrase(selected_style)

        page_terms: list[str] = []
        for page in pages[:3]:
            page_name = self._normalize_text(page.get("name", "")).replace("_", " ")
            if page_name and page_name not in page_terms:
                page_terms.append(page_name)

        page_hint = ", ".join(page_terms)
        queries = [
            f"{prompt_text} {style_phrase} website ui inspiration",
            f"{prompt_text} {style_phrase} landing page motion inspiration",
        ]
        if page_hint:
            queries.append(f"{prompt_text} {style_phrase} {page_hint} interface inspiration")

        deduped: list[str] = []
        seen: set[str] = set()
        for query in queries:
            normalized = self._normalize_text(query)
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(normalized)
        return deduped[:3]

    def _build_queries_with_llm(
        self,
        prompt: str,
        selected_style: str,
        pages: list[dict[str, Any]],
    ) -> list[str]:
        fallback_queries = self._build_queries_fallback(
            prompt=prompt,
            selected_style=selected_style,
            pages=pages,
        )
        page_names = [
            self._normalize_text(str(page.get("name", ""))).replace("_", " ")
            for page in pages[:4]
            if page.get("name")
        ]

        query_prompt = f"""
User request:
{self._normalize_text(prompt)[:220]}

Selected style:
{selected_style}

Planned pages:
{", ".join(page_names) if page_names else "home, features, pricing"}

Create 2 to 3 strong search queries for visual website inspiration research.
The queries should help retrieve premium references for:
- page hierarchy
- layout patterns
- motion cues
- design style alignment
"""

        try:
            raw = invoke_text_model(
                prompt=query_prompt,
                system_prompt=RESEARCH_QUERY_SYSTEM_PROMPT,
                model_name=RESEARCH_MODEL,
                temperature=0.2,
                max_completion_tokens=220,
            )
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                return fallback_queries
            payload = json.loads(match.group(0))
            queries = payload.get("queries", [])
            if not isinstance(queries, list):
                return fallback_queries

            cleaned: list[str] = []
            seen: set[str] = set()
            for query in queries:
                normalized = self._normalize_text(str(query))
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    cleaned.append(normalized)

            return cleaned[:3] or fallback_queries
        except Exception as exc:
            logger.warning("Research query LLM generation failed: %s", exc)
            return fallback_queries

    async def _search(self, query: str) -> list[dict[str, str]]:
        await self._ensure_tools()
        if not self.firecrawl_search_tool:
            logger.error("Firecrawl search tool is unavailable")
            return []

        try:
            result = await self.firecrawl_search_tool.ainvoke(
                {
                    "query": query,
                    "limit": 5,
                    "sources": [{"type": "web"}, {"type": "images"}],
                }
            )
        except Exception as exc:
            logger.error("Firecrawl search failed for '%s': %s", query, exc)
            return []

        payload = self._extract_payload(result)
        logger.info(
            "Firecrawl payload type for query '%s': %s",
            query,
            type(payload).__name__,
        )
        candidates = self._extract_candidates(payload)

        logger.info(
            "Firecrawl candidate count for query '%s': %s",
            query,
            len(candidates),
        )
        if candidates:
            sample = candidates[0]
            logger.info(
                "Firecrawl first candidate sample for query '%s': %s",
                query,
                self._normalize_text(str(sample))[:500],
            )
        else:
            logger.warning("Firecrawl returned no candidates for query '%s'", query)

        normalized: list[dict[str, str]] = []
        for item in candidates:
            if not isinstance(item, dict):
                text = self._normalize_text(str(item))
                if text:
                    normalized.append({"title": text[:80], "url": "", "snippet": text[:240]})
                continue

            title = self._normalize_text(
                item.get("title") or item.get("metadata", {}).get("title") or ""
            )
            url = self._normalize_text(item.get("url") or item.get("sourceURL") or "")
            snippet = self._normalize_text(
                item.get("description") or item.get("markdown") or item.get("content") or ""
            )

            if title or url or snippet:
                normalized.append(
                    {
                        "title": title[:120],
                        "url": url,
                        "snippet": snippet[:280],
                    }
                )

        logger.info(
            "Normalized Firecrawl results for query '%s': %s",
            query,
            len(normalized),
        )
        return normalized

    @staticmethod
    def _dedupe_references(items: list[dict[str, str]]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in items:
            key = (item.get("url", ""), item.get("title", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _build_summary(
        selected_style: str,
        pages: list[dict[str, Any]],
        references: list[dict[str, str]],
    ) -> str:
        page_names = [
            str(page.get("name", "")).replace("_", " ")
            for page in pages[:3]
            if page.get("name")
        ]
        titles = [item["title"] for item in references[:3] if item.get("title")]

        page_part = ", ".join(page_names) if page_names else "core website pages"
        title_part = "; ".join(titles) if titles else "no direct references found"

        return (
            f"Research focus: {selected_style.replace('_', ' ')}. "
            f"Primary pages: {page_part}. "
            f"Reference signals: {title_part}."
        )

    def _summarize_with_llm(
        self,
        prompt: str,
        selected_style: str,
        pages: list[dict[str, Any]],
        references: list[dict[str, str]],
    ) -> str:
        deterministic_summary = self._build_summary(
            selected_style=selected_style,
            pages=pages,
            references=references,
        )

        if not references:
            return deterministic_summary

        page_names = [
            str(page.get("name", "")).replace("_", " ")
            for page in pages[:4]
            if page.get("name")
        ]

        prompt_text = f"""
User request:
{self._normalize_text(prompt)[:220]}

Selected style:
{selected_style}

Primary pages:
{", ".join(page_names) if page_names else "core pages"}

Inspiration references:
{json.dumps(references[:5], indent=2)}

Write a concise research summary that captures:
- strongest visual patterns
- motion/interactivity cues
- composition or hierarchy ideas worth reusing
- anything to avoid if the references feel weak or generic
"""

        try:
            summary = invoke_text_model(
                prompt=prompt_text,
                system_prompt=RESEARCH_SUMMARY_SYSTEM_PROMPT,
                model_name=RESEARCH_MODEL,
                temperature=0.3,
                max_completion_tokens=300,
            )
            cleaned = self._normalize_text(summary)
            return cleaned or deterministic_summary
        except Exception as exc:
            logger.warning("Research LLM summary failed: %s", exc)
            return deterministic_summary

    async def gather_inspiration(
        self,
        prompt: str,
        selected_style: str,
        pages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        queries = self._build_queries_with_llm(
            prompt=prompt,
            selected_style=selected_style,
            pages=pages,
        )
        logger.info("Research queries: %s", queries)

        if not queries:
            return {
                "status": "empty",
                "queries": [],
                "references": [],
                "ui_patterns": [],
                "research_summary": "No research queries were generated.",
            }

        references: list[dict[str, str]] = []
        for query in queries:
            references.extend(await self._search(query))

        references = self._dedupe_references(references)[:8]
        status = "ready" if references else "empty"
        ui_patterns = [
            " | ".join(
                part for part in [item.get("title", ""), item.get("snippet", ""), item.get("url", "")]
                if part
            )
            for item in references
        ]

        return {
            "status": status,
            "queries": queries,
            "references": references,
            "ui_patterns": ui_patterns,
            "research_summary": self._summarize_with_llm(
                prompt=prompt,
                selected_style=selected_style,
                pages=pages,
                references=references,
            ),
        }


async def run_research_agent_test(
    prompt: str,
    selected_style: str,
    pages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    agent = ResearchAgent()
    return await agent.gather_inspiration(
        prompt=prompt,
        selected_style=selected_style,
        pages=pages or [],
    )


if __name__ == "__main__":
    import asyncio

    sample_prompt = (
        "Create a premium multi-page website for an AI startup called NeuraFlow "
        "that helps product teams automate internal workflows."
    )
    sample_pages = [
        {"name": "home"},
        {"name": "features"},
        {"name": "pricing"},
        {"name": "about"},
        {"name": "contact"},
    ]

    result = asyncio.run(
        run_research_agent_test(
            prompt=sample_prompt,
            selected_style="glassmorphism",
            pages=sample_pages,
        )
    )
    print(json.dumps(result, indent=2))
