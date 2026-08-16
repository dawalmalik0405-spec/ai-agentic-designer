from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import gemini_flash_llm
from agents.page_code_agent import DevServerManager
from pipeline_utils import resilient_ainvoke
from schema.asset_injection import (
    ApprovedAsset,
    AssetInjectionFileResult,
    AssetInjectionOutput,
)


logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
GENERATED_SITE_DIR = PROJECT_ROOT / "generated_site"
ASSETS_DIR = PROJECT_ROOT / "assets"


def _backend_public_url() -> str:
    return os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")


class AssetInjectionAgent:
    """Injects approved asset URLs into generated React page files."""

    def __init__(self):
        self.llm = gemini_flash_llm()

    def collect_approved_assets(self) -> list[ApprovedAsset]:
        registry_path = ASSETS_DIR / "registry.json"
        if not registry_path.exists():
            return []

        with open(registry_path, "r", encoding="utf-8") as file:
            registry = json.load(file)

        approved_assets: list[ApprovedAsset] = []
        for asset_id, entry in registry.get("assets", {}).items():
            raw_path = entry.get("file_path") or ""
            source_url = entry.get("source_url")
            public_url = source_url if str(raw_path).startswith(("http://", "https://")) else self._public_asset_url(raw_path)
            if not public_url:
                continue

            approved_assets.append(
                ApprovedAsset(
                    asset_id=asset_id,
                    name=Path(raw_path).name or asset_id,
                    asset_type=entry.get("asset_type", "image"),
                    purpose=entry.get("purpose", ""),
                    url=public_url,
                    page_name=entry.get("page_name"),
                    section_name=entry.get("section_name"),
                    dimensions=f"{entry.get('width', '')} x {entry.get('height', '')}".strip(),
                )
            )

        return approved_assets

    def _public_asset_url(self, raw_path: str) -> str | None:
        if not raw_path:
            return None

        path = Path(raw_path)
        if path.is_absolute():
            local_path = path
            try:
                relative_path = local_path.resolve().relative_to(ASSETS_DIR.resolve())
            except ValueError:
                return None
        else:
            parts = path.parts
            relative_path = Path(*parts[1:]) if parts and parts[0] == ASSETS_DIR.name else path
            local_path = ASSETS_DIR / relative_path

        if not local_path.exists():
            return None

        return f"{_backend_public_url()}/generated-assets/{relative_path.as_posix()}"

    def _page_files(self, generated_site_dir: Path = GENERATED_SITE_DIR) -> list[Path]:
        pages_dir = generated_site_dir / "src" / "pages"
        if not pages_dir.exists():
            return []
        return sorted(pages_dir.glob("*.tsx"))

    def _asset_matches_file(self, asset: ApprovedAsset, page_file: Path) -> bool:
        page_key = page_file.stem.lower()
        candidates = [
            asset.page_name or "",
            asset.section_name or "",
            asset.asset_id,
            asset.purpose,
        ]
        candidate_text = " ".join(candidates).lower()
        return page_key in candidate_text

    def _target_page_file(
        self,
        target_page_name: str | None,
        generated_site_dir: Path,
    ) -> Path | None:
        if not target_page_name:
            return None

        words = re.findall(r"[A-Za-z0-9]+", target_page_name)
        if not words:
            return None

        module_name = "".join(word[:1].upper() + word[1:] for word in words)
        pages_dir = generated_site_dir / "src" / "pages"
        candidates = [pages_dir / f"{module_name}.tsx"]
        if target_page_name.strip().lower() in {"home", "homepage", "index"}:
            candidates.extend([pages_dir / "Home.tsx", pages_dir / "Homepage.tsx"])

        for page_file in candidates:
            if page_file.exists():
                return page_file

        normalized_target = "".join(words).lower()
        for page_file in self._page_files(generated_site_dir):
            if re.sub(r"[^a-z0-9]+", "", page_file.stem.lower()) == normalized_target:
                return page_file

        return None

    def _extract_tsx(self, content: str) -> str:
        match = re.search(r"```(?:tsx|typescript|jsx|javascript)?\s*(.*?)```", content, re.DOTALL)
        code = match.group(1).strip() if match else content.strip()
        if "export default" not in code:
            raise ValueError("Model response did not contain a complete TSX component.")
        return code + "\n"

    def _system_prompt(self) -> str:
        return """You are the Asset Injection Agent.

Your only job is to inject approved asset URLs into an existing React TSX page.

Rules:
- Preserve the current page structure, layout, text, colors, components, and imports unless an import change is strictly required.
- Do not redesign the page.
- Do not add or remove sections.
- Do not rewrite copy.
- Do not invent new asset URLs.
- Use only the approved assets provided by the user message.
- Prefer placing assets in existing visual areas, image placeholders, hero visuals, product cards, galleries, and background image containers.
- If the page already has img tags or placeholder visual divs, replace those visual placeholders with approved assets.
- Add useful alt text derived from the asset purpose.
- Return only one complete TSX code block.
"""

    def _user_prompt(self, relative_path: str, code: str, assets: list[ApprovedAsset]) -> str:
        assets_json = json.dumps([asset.model_dump() for asset in assets], indent=2)
        return f"""Inject the approved assets into this page file.

File path:
{relative_path}

Approved assets:
{assets_json}

Current TSX:
```tsx
{code}
```
"""

    async def inject(
        self,
        approved_assets: list[ApprovedAsset] | None = None,
        generated_site_dir: str | Path | None = GENERATED_SITE_DIR,
        target_page_name: str | None = None,
    ) -> AssetInjectionOutput:
        site_dir = Path(generated_site_dir) if generated_site_dir else GENERATED_SITE_DIR
        assets = approved_assets or self.collect_approved_assets()
        target_page_file = self._target_page_file(target_page_name, site_dir)
        page_files = [target_page_file] if target_page_file else self._page_files(site_dir)

        if not assets:
            return AssetInjectionOutput(status="skipped", errors=["No approved assets found."])
        if not page_files:
            return AssetInjectionOutput(status="skipped", errors=["No generated TSX page files found."])

        file_results: list[AssetInjectionFileResult] = []
        updated_files: list[str] = []
        all_injected_assets: list[str] = []

        for page_file in page_files:
            relative_path = page_file.relative_to(site_dir).as_posix()
            matching_assets = assets if target_page_name else [asset for asset in assets if self._asset_matches_file(asset, page_file)]
            if not matching_assets:
                file_results.append(AssetInjectionFileResult(path=relative_path, status="skipped"))
                continue

            original_code = page_file.read_text(encoding="utf-8")
            try:
                response = await resilient_ainvoke(
                    self.llm,
                    [
                        SystemMessage(content=self._system_prompt()),
                        HumanMessage(content=self._user_prompt(relative_path, original_code, matching_assets)),
                    ],
                    "asset_injection",
                )
                raw = response.content if hasattr(response, "content") else str(response)
                updated_code = self._extract_tsx(raw)

                if updated_code.strip() == original_code.strip():
                    file_results.append(AssetInjectionFileResult(path=relative_path, status="unchanged"))
                    continue

                page_file.write_text(updated_code, encoding="utf-8")
                injected_ids = [asset.asset_id for asset in matching_assets]
                updated_files.append(relative_path)
                all_injected_assets.extend(injected_ids)
                file_results.append(
                    AssetInjectionFileResult(
                        path=relative_path,
                        status="updated",
                        injected_assets=injected_ids,
                    )
                )
            except Exception as exc:
                logger.exception("Asset injection failed for %s", relative_path)
                page_file.write_text(original_code, encoding="utf-8")
                file_results.append(
                    AssetInjectionFileResult(
                        path=relative_path,
                        status="failed",
                        error=str(exc),
                    )
                )

        status = "success" if updated_files else "skipped"
        errors = [result.error for result in file_results if result.error]
        if errors:
            status = "partial" if updated_files else "failed"

        return AssetInjectionOutput(
            status=status,
            updated_files=updated_files,
            injected_assets=list(dict.fromkeys(all_injected_assets)),
            file_results=file_results,
            errors=errors,
        )

    async def start_dev_server(self, generated_site_dir: str | Path | None = GENERATED_SITE_DIR) -> dict:
        site_dir = Path(generated_site_dir) if generated_site_dir else GENERATED_SITE_DIR
        result = await DevServerManager().install_and_start(str(site_dir))
        return {
            "dev_server_status": result["build_status"],
            "preview_url": result.get("preview_url"),
            "log_tail": result.get("log_tail", []),
        }
