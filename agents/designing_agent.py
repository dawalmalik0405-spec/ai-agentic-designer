"""
Designing Agent
----------------
Generates premium UI design systems, animation specifications, and per-page component templates.
Uses real MCP tools via the centralized MCPManager.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any

from agents.llm import invoke_text_model
from mcp_tools.initialize_mcps import get_tools_for_agent, get_mcp_manager

logger = logging.getLogger(__name__)


class DesigningAgent:
    """Agent responsible for creating design systems and animation specs."""

    def __init__(self):
        self._tools_loaded = False
        self.context7_tool = None
        self.filesystem_tool = None

    async def _ensure_tools(self):
        if not self._tools_loaded:
            tools = await get_tools_for_agent("design")
            # Find context7 tool by name
            for t in tools:
                if "context7" in t.name.lower():
                    self.context7_tool = t
                if any(x in t.name.lower() for x in ["file", "write", "read"]):
                    self.filesystem_tool = t
            self._tools_loaded = True

    async def _fetch_doc_examples(self, lib_name: str, query: str) -> List[str]:
        await self._ensure_tools()
        try:
            # Use the context7 tool via ainvoke
            resp = await self.context7_tool.ainvoke({"query": query, "libraries": [lib_name]})
            # resp may be a dict or ToolMessage; adapt
            if isinstance(resp, dict):
                return resp.get("results", [])
            else:
                # possibly a ToolMessage with content attribute
                content = getattr(resp, "content", None)
                if content:
                    import json
                    try:
                        data = json.loads(content)
                        return data.get("results", [])
                    except Exception:
                        return []
        except Exception as exc:
            logger.error(f"Context7 lookup failed for {lib_name}: {exc}")
        return []

    async def _persist_design_token(self, style_name: str, token_dict: Dict) -> None:
        await self._ensure_tools()
        path = f"design_tokens/{style_name}.json"
        try:
            await self.filesystem_tool.ainvoke({
                "operation": "write",
                "path": path,
                "content": json.dumps(token_dict, indent=2)
            })
        except Exception as exc:
            logger.error(f"Failed to write design token for {style_name}: {exc}")

    async def _generate_style_system(self, style_name: str, doc_snippets: List[str]) -> Dict:
        doc_blob = "\n".join(doc_snippets)
        prompt = (
            f"You are a senior front-end designer. Using the following documentation snippets,\n"
            f"create a premium design system for the style *{style_name}*.\n"
            "Include:\n"
            "- A color palette (primary, secondary, background, accent).\n"
            "- Typography settings (font families, sizes, weights).\n"
            "- Motion defaults (easing curves, durations) that work well with Three.js and GSAP.\n"
            "- Any recommended Tailwind utility extensions.\n\n"
            f"Documentation snippets:\n{doc_blob}\n"
            "Return **only** a JSON object with keys: colors, typography, motion."
        )
        raw = invoke_text_model(prompt, model_name="qwen/qwen3-next-80b-a3b-instruct", temperature=0.6)
        try:
            start = raw.find('{')
            end = raw.rfind('}')
            json_str = raw[start:end + 1]
            token_dict = json.loads(json_str)
        except Exception as exc:
            logger.error(f"Failed to parse design system JSON for {style_name}: {exc}\nRaw output: {raw}")
            token_dict = {}
        return token_dict

    async def _generate_animation_spec(self, animation_intent: str, doc_snippets: List[str]) -> Dict:
        doc_blob = "\n".join(doc_snippets)
        prompt = (
            f"Using the following documentation snippets, produce a concise animation spec for a\n"
            f"{animation_intent}. Return a JSON array where each entry contains:\n"
            "- type (e.g., 'gsap', 'r3f')\n"
            "- selector or target reference\n"
            "- properties to animate\n"
            "- duration (ms)\n"
            "- easing\n"
            "- optional fallback for non-WebGL browsers.\n"
            f"Documentation snippets:\n{doc_blob}\n"
            "Only return the JSON array, no extra text."
        )
        raw = invoke_text_model(prompt, model_name="qwen/qwen3-next-80b-a3b-instruct", temperature=0.6)
        try:
            start = raw.find('[')
            end = raw.rfind(']')
            json_str = raw[start:end + 1]
            spec = json.loads(json_str)
        except Exception as exc:
            logger.error(f"Failed to parse animation spec JSON for {animation_intent}: {exc}\nRaw output: {raw}")
            spec = []
        return spec

    async def generate_for_page(self, page_blueprint: Dict) -> Dict:
        style_name = page_blueprint.get("style", "minimalism")
        animation_intent = page_blueprint.get("animation_intent", "basic fade in")

        # Ensure MCP tools are loaded
        await self._ensure_tools()

        # Pull relevant docs
        doc_snippets = await self._fetch_doc_examples("Three.js", f"{style_name} style examples with Three.js")
        doc_snippets += await self._fetch_doc_examples("GSAP", f"{style_name} animation patterns using GSAP")

        # Generate design system
        design_system = await self._generate_style_system(style_name, doc_snippets)
        await self._persist_design_token(style_name, design_system)

        # Generate animation spec
        animation_spec = await self._generate_animation_spec(animation_intent, doc_snippets)

        # Build template
        template = {
            "page_name": page_blueprint.get("name", "unknown"),
            "style": style_name,
            "design_system": design_system,
            "animation_spec": animation_spec,
            "component": f"export default function {page_blueprint.get('name', 'Page').title().replace('_','')}() {{\n  // TODO: Insert generated JSX using design_system & animation_spec\n}}"
        }

        # Persist template
        tmpl_path = f"page_templates/{page_blueprint.get('name', 'page')}.json"
        try:
            await self.filesystem_tool.ainvoke({
                "operation": "write",
                "path": tmpl_path,
                "content": json.dumps(template, indent=2)
            })
        except Exception as exc:
            logger.error(f"Failed to write page template {tmpl_path}: {exc}")

        return {
            "design_system": design_system,
            "animation_spec": animation_spec,
            "page_template": template,
        }


# Singleton
_designing_agent_instance: DesigningAgent | None = None


def get_designing_agent() -> DesigningAgent:
    global _designing_agent_instance
    if _designing_agent_instance is None:
        _designing_agent_instance = DesigningAgent()
    return _designing_agent_instance
