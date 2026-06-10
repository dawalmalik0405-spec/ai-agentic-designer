import json
import logging
import os
import sys
from typing import Any




CURRENT_DIR = os.path.dirname(__file__)
PACKAGE_ROOT = os.path.dirname(CURRENT_DIR)
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)

from mcp_tools.firecrawl_research import run_firecrawl_research


logger = logging.getLogger(__name__)




def _compact_pages(pages: Any) -> list[dict[str, Any]]:
    raw_pages = pages.get("pages", []) if isinstance(pages, dict) else pages
    if not isinstance(raw_pages, list):
        return []

    compact: list[dict[str, Any]] = []
    for page in raw_pages:
        if not isinstance(page, dict):
            continue
        compact.append(
            {
                "name": page.get("name", ""),
                "route": page.get("route", ""),
                "type": page.get("type", ""),
                "goal": page.get("goal", ""),
                "sections": page.get("sections", []),
                "ui_sections": page.get("ui_sections", []),
            }
        )
    return compact


class ResearchAgent:
    async def gather_inspiration(
        self,
        prompt: str,
        selected_style: str,
        pages: list[dict[str, Any]] | dict[str, Any],
    ) -> dict[str, Any]:

        planned_pages = _compact_pages(pages)
        research_prompt = f"""
User request:
{prompt}

Selected style:
{selected_style}

Planner page output:
{json.dumps(planned_pages, indent=2)}

Research premium modern websites that match this product.

Find:
- page layouts
- section ordering
- hero section ideas
- feature section ideas
- CTA patterns
- typography direction
- color direction
- animations
- interactions
- premium visual details

Return structured research.
""".strip()

        print("\n" + "=" * 100)
        print("RESEARCH PROMPT:")
        print(research_prompt)
        print("=" * 100 + "\n")
        
        result = await run_firecrawl_research(
            research_prompt
        )

        payload = result.get("data", result)
        payload = result.get("data", result)

        payload["raw_research"] = result
        payload.setdefault("queries", [])
        payload.setdefault("references", [])
        payload.setdefault("ui_patterns", [])
        payload.setdefault("layout_patterns", [])
        payload.setdefault("component_patterns", [])
        payload.setdefault("animation_patterns", [])
        payload.setdefault("premium_requirements", [])
        payload.setdefault("page_research", {})
        payload.setdefault("research_summary", "")
        payload["status"] = "ready"

        return payload
    

if __name__ == "__main__":
    import asyncio

    pages = [
        {
            "name": "Home",
            "route": "/",
            "type": "landing",
            "goal": "Introduce eco packaging brand",
            "sections": ["hero", "features", "products", "contact"],
        }
    ]

    result = asyncio.run(
        ResearchAgent().gather_inspiration(
            "Website for eco-friendly packaging startup",
            "glassmorphism",
            pages,
        )
    )
    print(json.dumps(result, indent=2))
