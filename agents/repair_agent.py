import asyncio
import json
from typing import Any

try:
    from .llm import CODE_MODEL, invoke_text_model_async
except ImportError:
    from agents.llm import CODE_MODEL, invoke_text_model_async


SYSTEM_PROMPT = """
You are a senior frontend repair engineer.

You fix generated React/Vite project files.

Rules:
- Return the full corrected file contents only
- No markdown
- No explanations
- Keep existing project structure intact
- Fix only the requested issues
- Preserve imports/exports unless they are part of the bug
- If a file references missing local assets, replace those references with self-contained JSX/Tailwind UI
- Do not introduce new missing asset paths
"""


def _group_issues_by_file(issues: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}

    for issue in issues:
        path = issue.get("file")
        if not path:
            continue
        grouped.setdefault(path, []).append(issue)

    return grouped


async def _repair_file(
    path: str,
    source: str,
    issues: list[dict[str, str]],
    files: dict[str, str],
    prompt: str,
    images: dict[str, Any],
) -> tuple[str, str]:
    prompt_text = f"""
User request:
{prompt}

Project file paths:
{json.dumps(sorted(files.keys()), indent=2)}

Generated image data:
{json.dumps(images, indent=2)}

Current file path:
{path}

Current file contents:
{source}

Issues to fix:
{json.dumps(issues, indent=2)}

Return the corrected full file contents only.
"""

    repaired = await invoke_text_model_async(
        prompt=prompt_text,
        system_prompt=SYSTEM_PROMPT,
        model_name=CODE_MODEL,
        temperature=0.2,
    )

    return path, repaired.strip()


def repair_project(state: dict[str, Any]) -> dict[str, Any]:
    files = dict(state.get("files", {}))
    review = state.get("review", {})
    issues = review.get("issues", [])
    grouped = _group_issues_by_file(issues)

    if not grouped:
        return {
            "files": files,
            "repair_count": state.get("repair_count", 0),
        }

    async def _repair_all() -> dict[str, str]:
        tasks = []

        for path, file_issues in grouped.items():
            if path not in files:
                continue
            print(f"[repair] {path}: started", flush=True)
            tasks.append(
                _repair_file(
                    path=path,
                    source=files[path],
                    issues=file_issues,
                    files=files,
                    prompt=state.get("prompt", ""),
                    images=state.get("images", {}),
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"[repair] file repair failed: {result}", flush=True)
                continue

            path, repaired = result
            files[path] = repaired
            print(f"[repair] {path}: completed", flush=True)

        return files

    repaired_files = asyncio.run(_repair_all())

    return {
        "files": repaired_files,
        "repair_count": state.get("repair_count", 0) + 1,
    }
