import os
import re
import json
import logging

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "generated_site")
GENERATED_ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

SYSTEM_PROMPT = """
You are an expert frontend engineer specializing in visual polish and GSAP scroll animations.

Your task is to parse a React page component and replace all placeholder images with real generated visual assets.
You will also inject premium GSAP ScrollTrigger parallax scroll animation behaviors for hero/background images on the Homepage (landing page) if requested.
"""

class AssetInjectionAgent:
    def __init__(self):
        pass

    def _module_name(self, name: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", name)
        if not words:
            return "Page"
        return "".join(word[:1].upper() + word[1:] for word in words)

    async def inject_assets_to_page(self, state: dict, page_name: str, assets_mapping: dict[str, str]) -> str:
        module_name = self._module_name(page_name)
        page_path = os.path.join(OUTPUT_DIR, "src", "pages", f"{module_name}.tsx")

        if not os.path.isfile(page_path):
            raise FileNotFoundError(f"Page file not found at {page_path}")

        with open(page_path, "r", encoding="utf-8") as file:
            source = file.read()

        updated = source
        injected_count = 0
        for target_asset_id, public_url in assets_mapping.items():
            next_source, changed = self._replace_matching_asset(updated, target_asset_id, public_url)
            if not changed:
                next_source, changed = self._replace_first_placeholder(updated, target_asset_id, public_url)
            if changed:
                updated = next_source
                injected_count += 1

        if updated != source:
            with open(page_path, "w", encoding="utf-8") as file:
                file.write(updated)

        return f"Injected {injected_count} asset(s) into src/pages/{module_name}.tsx"

    async def inject_assets(self):
        config_path = os.path.join(GENERATED_ASSETS_DIR, "injection_config.json")
        if not os.path.isfile(config_path):
            logger.error("No injection config found.")
            return

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        pages_dir = os.path.join(OUTPUT_DIR, "src", "pages")
        if not os.path.isdir(pages_dir):
            return

        assets = [
            asset for asset in config.get("assets", [])
            if self._asset_public_url(asset.get("asset_id"))
        ]

        if not assets:
            logger.warning("No generated asset files found for injection config.")
            return

        for filename in os.listdir(pages_dir):
            if not filename.endswith((".tsx", ".jsx")):
                continue

            module_name = os.path.splitext(filename)[0]
            page_assets = [
                asset for asset in assets
                if not asset.get("page_name") or self._module_name(asset["page_name"]) == module_name
            ]
            if not page_assets:
                continue

            page_path = os.path.join(pages_dir, filename)
            with open(page_path, "r", encoding="utf-8") as file:
                source = file.read()

            updated = source
            injected_count = 0

            for asset in page_assets:
                asset_id = asset["asset_id"]
                target_asset_id = asset.get("target_asset_id") or asset_id
                public_url = self._asset_public_url(asset_id)
                if not public_url:
                    continue

                next_source, changed = self._replace_matching_asset(updated, target_asset_id, public_url)
                if not changed:
                    # Explicit placement must never be redirected to a different section.
                    if asset.get("target_asset_id"):
                        logger.warning("No placeholder '%s' found in %s", target_asset_id, filename)
                        continue
                    next_source, changed = self._replace_first_placeholder(updated, asset_id, public_url)

                if changed:
                    updated = next_source
                    injected_count += 1

            if updated != source:
                with open(page_path, "w", encoding="utf-8") as file:
                    file.write(updated)
                logger.info("Injected %s asset(s) into %s", injected_count, filename)

    def _asset_public_url(self, asset_id: str | None) -> str | None:
        if not asset_id:
            return None

        if os.path.isfile(os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.mp4")):
            return f"/assets/{asset_id}.mp4"

        if os.path.isfile(os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png")):
            return f"/assets/{asset_id}.png"

        return None

    def _replace_matching_asset(self, source: str, asset_id: str, public_url: str) -> tuple[str, bool]:
        image_pattern = re.compile(
            rf"<img\b(?=[^>]*\bdata-asset-id=[\"']{re.escape(asset_id)}[\"'])(?P<attrs>[^>]*)>",
            re.DOTALL,
        )

        def replace_image(match: re.Match) -> str:
            attrs = match.group("attrs")
            attrs = self._replace_or_add_attr(attrs, "src", public_url)
            return f"<img{attrs}>"

        updated, count = image_pattern.subn(replace_image, source)
        return updated, count > 0

    def _replace_first_placeholder(self, source: str, asset_id: str, public_url: str) -> tuple[str, bool]:
        image_pattern = re.compile(
            r"<img\b(?=[^>]*\bsrc=[\"']https://placehold\.co/[^\"']+[\"'])(?P<attrs>[^>]*)>",
            re.DOTALL,
        )
        match = image_pattern.search(source)
        if not match:
            return source, False

        attrs = match.group("attrs")
        attrs = self._replace_or_add_attr(attrs, "src", public_url)
        attrs = self._replace_or_add_attr(attrs, "data-asset-id", asset_id)
        updated_tag = f"<img{attrs}>"
        return source[:match.start()] + updated_tag + source[match.end():], True

    def _replace_or_add_attr(self, attrs: str, name: str, value: str) -> str:
        attr_pattern = re.compile(rf"\b{name}=[\"'][^\"']*[\"']")
        replacement = f'{name}="{value}"'
        if attr_pattern.search(attrs):
            return attr_pattern.sub(replacement, attrs, count=1)
        return f'{attrs} {replacement}'
