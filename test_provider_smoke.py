"""Standalone smoke runner for providers (no pytest).

Saves outputs to `outputs/` and prints progress.
Run: `python provider_smoke_runner.py`
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp

from mcp_tools.asset_generation.providers.pollinations_provider import PollinationsProvider
from mcp_tools.asset_generation.providers.search_provider import SearchProvider, SearchQuery
from mcp_tools.asset_generation.providers.icon_provider import IconLibraryProvider
from mcp_tools.asset_generation.providers.css_provider import CSSLibraryProvider, CSSLibrary


OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


async def fetch_and_save(url: str, out_path: Path) -> None:
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status} fetching {url}")
            data = await resp.read()
            out_path.write_bytes(data)


async def test_pollinations():
    print("[pollinations] Generating image...")
    provider = PollinationsProvider()
    try:
        img_bytes = await provider.generate_image(
            "A cozy cabin in the woods, digital illustration", width=512, height=512, model="flux"
        )
        out_file = OUTPUT_DIR / "pollinations_test.png"
        out_file.write_bytes(img_bytes)
        print(f"[pollinations] Saved {out_file} ({out_file.stat().st_size} bytes)")
    except Exception as e:
        print(f"[pollinations] Failed: {e}")


async def test_stock_search():
    print("[stock] Searching Unsplash for candidates...")
    provider = SearchProvider()
    query = SearchQuery(keywords=["nature", "landscape"], max_results=5)
    try:
        candidates = await provider.search(query, provider="unsplash")
    except Exception as e:
        print(f"[stock] Search skipped/failure: {e}")
        return

    if not candidates:
        print("[stock] No candidates returned")
        return

    first = candidates[0]
    print(f"[stock] Selected candidate: {first.candidate_id} from {first.source}")
    out_file = OUTPUT_DIR / f"stock_{first.candidate_id}.jpg"

    try:
        await fetch_and_save(first.source_url, out_file)
        print(f"[stock] Saved {out_file} ({out_file.stat().st_size} bytes)")
    except Exception as e:
        print(f"[stock] Download failed: {e}")


async def test_icon_and_css():
    icon_provider = IconLibraryProvider()
    css_provider = CSSLibraryProvider()

    print("[icon] Getting Feather 'github' icon URL...")
    icon = icon_provider.get_icon_url("github")
    if icon is None:
        print("[icon] Icon not found")
    else:
        out_svg = OUTPUT_DIR / f"icon_{icon.icon_id}.svg"
        try:
            await fetch_and_save(icon.svg_url, out_svg)
            print(f"[icon] Saved {out_svg} ({out_svg.stat().st_size} bytes)")
        except Exception as e:
            print(f"[icon] Failed to fetch icon: {e}")

    print("[css] Getting Bootstrap Icons CSS asset...")
    css_asset = css_provider.get_library_css(CSSLibrary.BOOTSTRAP_ICONS)
    if css_asset is None:
        print("[css] CSS asset not found")
    else:
        out_css = OUTPUT_DIR / f"css_{css_asset.asset_id}.txt"
        try:
            # Some CDN URLs return HTML or require additional handling; fetch raw bytes
            await fetch_and_save(css_asset.cdn_url, out_css)
            print(f"[css] Saved {out_css} ({out_css.stat().st_size} bytes)")
        except Exception as e:
            print(f"[css] Failed to fetch CSS asset: {e}")


async def main():
    await test_pollinations()
    await test_stock_search()
    await test_icon_and_css()


if __name__ == "__main__":
    asyncio.run(main())