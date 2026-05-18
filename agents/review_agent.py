"""
Review Agent
-------------
Validates generated pages for visual consistency, performance, and animation quality.
Uses real Playwright MCP tool via centralized MCPManager.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from agents.llm import CODE_MODEL, invoke_structured_model
from mcp_tools.initialize_mcps import get_tools_for_agent

logger = logging.getLogger(__name__)


class ReviewIssue(BaseModel):
    file: str
    severity: str
    summary: str
    fix: str


class ReviewResult(BaseModel):
    needs_repair: bool
    summary: str
    issues: list[ReviewIssue] = Field(default_factory=list)


SYSTEM_PROMPT = """
You are a strict senior frontend reviewer.

You review generated React/Vite projects for high-confidence problems only.

Focus on:
- invalid JSX
- broken imports
- route/component mismatches
- obvious runtime failures
- malformed config files
- broken package structure
- undeclared local asset references

Assume this stack when shown in the files:
- Vite
- React
- Tailwind CSS v4
- @tailwindcss/vite

Tailwind v4 notes:
- `@import "tailwindcss";` inside a CSS file is valid when the project uses the Vite Tailwind plugin.
- Do not require `tailwind.config.js`, `postcss.config.js`, or `@tailwind` directives unless the shown files clearly need them.

Rules:
- Return valid JSON only
- Be conservative
- Do not invent speculative issues
- Do not flag issues caused only by truncated file snapshots
- Do not suggest config/package changes unless the provided file contents show a concrete mismatch
- If the project is acceptable, return needs_repair=false
"""


def _dump_model(model: BaseModel) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _collect_project_files(files: dict[str, str]) -> dict[str, str]:
    interesting = {}
    for path, content in files.items():
        if path.endswith((".jsx", ".js", ".css", ".html", ".json")):
            interesting[path] = content
    return interesting


def _truncate_content(content: str, limit: int = 1800) -> str:
    normalized = content.strip()
    return normalized if len(normalized) <= limit else normalized[:limit]


def _build_review_snapshot(state: dict[str, Any], files: dict[str, str]) -> dict[str, Any]:
    page_specs = state.get("pages", {}).get("pages", [])
    image_map = state.get("images", {}).get("pages", {})

    snapshot_files: dict[str, str] = {}
    always_include = {"src/App.jsx", "src/main.jsx", "src/styles.css", "vite.config.js", "package.json"}

    for path in always_include:
        if path in files:
            snapshot_files[path] = _truncate_content(files[path], limit=5000)

    for page in page_specs:
        page_name = page.get("name", "")
        if not page_name:
            continue
        component_name = "".join(word.capitalize() for word in page_name.split("_"))
        path = f"src/pages/{component_name}.jsx"
        if path in files:
            snapshot_files[path] = _truncate_content(files[path], limit=12000)

    return {
        "selected_style": state.get("selected_style", "minimalism"),
        "page_count": len(page_specs),
        "pages": [
            {
                "name": page.get("name", ""),
                "route": page.get("route", "/"),
                "sections": page.get("sections", []),
                "has_generated_images": page.get("name", "") in image_map,
            }
            for page in page_specs
        ],
        "files": snapshot_files,
    }


LOCAL_ASSET_PATTERN = re.compile(
    r"""(?:
        src|href|poster
      )\s*=\s*["']([^"']+)["']
      |
      url\(\s*["']?([^"')]+)["']?\s*\)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _is_local_asset_reference(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return False
    if lowered.startswith(("http://", "https://", "data:", "blob:", "#", "mailto:", "tel:")):
        return False
    return bool(
        lowered.startswith(("/", "./", "../", "assets/", "public/"))
        or re.search(r"\.(svg|png|jpe?g|gif|webp|avif|mp4|webm|mov)(?:[?#].*)?$", lowered)
    )


def _asset_exists_in_project(path: str, files: dict[str, str]) -> bool:
    normalized = path.lstrip("/")
    candidates = {
        normalized,
        f"public/{normalized}",
        f"src/{normalized}",
    }
    return any(candidate in files for candidate in candidates)


def _find_missing_asset_issues(files: dict[str, str]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    for path, content in files.items():
        if not path.endswith((".jsx", ".js", ".css", ".html")):
            continue

        seen_refs: set[str] = set()

        for match in LOCAL_ASSET_PATTERN.finditer(content):
            ref = (match.group(1) or match.group(2) or "").strip()
            if not _is_local_asset_reference(ref):
                continue
            if ref in seen_refs:
                continue
            seen_refs.add(ref)
            if _asset_exists_in_project(ref, files):
                continue

            issues.append(
                {
                    "file": path,
                    "severity": "high",
                    "summary": f"References missing local asset '{ref}'.",
                    "fix": (
                        "Remove the missing local asset dependency and replace it with a "
                        "self-contained JSX/Tailwind treatment such as gradients, inline SVG, "
                        "or decorative divs."
                    ),
                }
            )

    return issues


def _find_missing_generated_image_usage(state: dict[str, Any], files: dict[str, str]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    image_map = state.get("images", {}).get("pages", {})
    pages = state.get("pages", {}).get("pages", [])

    for page in pages:
        page_name = page.get("name")
        if not page_name:
            continue

        page_file = f"src/pages/{''.join(word.capitalize() for word in page_name.split('_'))}.jsx"
        page_code = files.get(page_file, "")
        page_images = image_map.get(page_name, {})
        hero_url = page_images.get("hero_url", "")
        background_url = page_images.get("background_url", "")
        sections = [str(section).lower() for section in page.get("sections", [])]
        requires_generated_visual = bool(page.get("requires_generated_visual", False))

        if not page_code or not page_images:
            continue

        needs_visual = requires_generated_visual or any(
            token in {"hero", "showcase", "banner", "product_detail", "gallery", "demo_preview"}
            for token in sections
        )
        if not needs_visual:
            continue

        if hero_url and hero_url in page_code:
            continue
        if background_url and background_url in page_code:
            continue

        issues.append(
            {
                "file": page_file,
                "severity": "high" if requires_generated_visual else "medium",
                "summary": "Page did not use the generated visual URL for a required premium visual section.",
                "fix": (
                    "Integrate one of the provided generated image URLs into the hero/showcase area "
                    "with a production-quality img or background treatment."
                ),
            }
        )

    return issues


def _dedupe_issues(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, str]] = []

    for issue in issues:
        key = (
            issue.get("file", ""),
            issue.get("summary", ""),
            issue.get("fix", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)

    return deduped


async def _run_playwright_checks(url: str, state: dict) -> dict:
    """Run Playwright MCP checks for visual and performance validation."""
    if not url:
        return {"skipped": True, "reason": "No preview URL provided"}

    try:
        tools = await get_tools_for_agent("review")
        tool_map = {tool.name: tool for tool in tools}
        navigate_tool = tool_map.get("browser_navigate")
        snapshot_tool = tool_map.get("browser_snapshot")
        console_tool = tool_map.get("browser_console_messages")

        if not navigate_tool:
            logger.error("No browser_navigate tool found")
            return {}

        await navigate_tool.ainvoke({"url": url})

        snapshot_result = None
        console_result = None
        if snapshot_tool:
            snapshot_result = await snapshot_tool.ainvoke({"depth": 3, "boxes": False})
        if console_tool:
            console_result = await console_tool.ainvoke({"level": "warning"})

        return {
            "snapshot": snapshot_result,
            "console": console_result,
            "issues": [],
        }
    except Exception as exc:
        logger.error(f"Playwright check failed: {exc}")
    return {}


def review_project(state: dict[str, Any]) -> dict[str, Any]:
    import asyncio
    files = _collect_project_files(state.get("files", {}))
    review_snapshot = _build_review_snapshot(state=state, files=files)
    deterministic_issues = _find_missing_asset_issues(files) + _find_missing_generated_image_usage(
        state=state,
        files=files,
    )

    # Run Playwright MCP checks (synchronous wrapper around async function)
    preview_url = state.get("preview_url")
    if preview_url:
        try:
            playwright_results = asyncio.run(_run_playwright_checks(preview_url, state))
        except Exception as exc:
            logger.error(f"Playwright check failed: {exc}")
            playwright_results = {}
    else:
        playwright_results = {"skipped": True, "reason": "No preview URL provided"}

    # Merge Playwright issues if any
    if playwright_results.get("issues"):
        deterministic_issues.extend(playwright_results["issues"])
    # Attach playwright results to state for later use
    state["playwright_results"] = playwright_results

    prompt = f"""
User request:
{state.get("prompt", "")}

Project snapshot:
{json.dumps(review_snapshot, indent=2)}

Review this generated project and return only high-confidence issues that should trigger repair.
Flag undeclared local asset references whenever a file points to local media that does not exist in the packaged project.

Return JSON in this format:
{{
  "needs_repair": true,
  "summary": "",
  "issues": [
    {{
      "file": "src/App.jsx",
      "severity": "high",
      "summary": "",
      "fix": ""
    }}
  ]
}}

Important:
- Some file contents may be truncated for length.
- Do not report malformed syntax if the only evidence is that the snapshot ends abruptly.
- Only report configuration/package issues when the shown file contents demonstrate a real mismatch.
- Treat Tailwind v4 with the Vite plugin as valid when you see `@tailwindcss/vite` and `@import "tailwindcss";`.
"""

    result = invoke_structured_model(
        prompt=prompt,
        schema=ReviewResult,
        system_prompt=SYSTEM_PROMPT,
        model_name=CODE_MODEL,
        temperature=0.2,
        max_attempts=2,
        max_completion_tokens=1200,
    )

    payload = _dump_model(result)
    llm_issues = [_dump_model(issue) for issue in result.issues]
    payload["issues"] = _dedupe_issues(llm_issues + deterministic_issues)
    payload["needs_repair"] = bool(payload["issues"])
    if payload["needs_repair"] and not payload.get("summary"):
        payload["summary"] = "High-confidence review issues found."
    return payload
