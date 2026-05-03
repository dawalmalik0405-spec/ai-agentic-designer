import json
from typing import Any

try:
    from ..mcp_server.tools.image_tool import build_generated_image_url
except ImportError:
    from mcp_server.tools.image_tool import build_generated_image_url


def _page_images(page: dict[str, Any], design: dict[str, Any], selected_style: str) -> dict[str, str]:
    page_name = page.get("name", "page")
    goal = page.get("goal", "")
    sections = ", ".join(page.get("sections", []))
    palette = design.get("palette", {})
    style_family = design.get("style_family", selected_style)
    mood = ", ".join(design.get("brand_mood", []))
    background = palette.get("background", "")
    accent = palette.get("accent", "")

    base_prompt = (
        f"premium website visual, {selected_style}, {style_family}, "
        f"page {page_name}, goal: {goal}, sections: {sections}, mood: {mood}, "
        f"background color {background}, accent color {accent}, clean editorial composition, "
        f"high-end product render, cinematic lighting, no text, no watermark"
    )

    hero_prompt = (
        f"{base_prompt}, hero image, sharp focal subject, premium product marketing photography"
    )
    background_prompt = (
        f"{base_prompt}, abstract background plate, atmospheric depth, decorative composition"
    )

    return {
        "hero_url": build_generated_image_url(
            hero_prompt,
            width=1600,
            height=1000,
            seed_key=f"{selected_style}:{page_name}:hero",
        ),
        "background_url": build_generated_image_url(
            background_prompt,
            width=1600,
            height=1200,
            seed_key=f"{selected_style}:{page_name}:background",
        ),
        "hero_alt": f"{page_name.replace('_', ' ').title()} hero visual",
        "hero_prompt": hero_prompt,
        "background_prompt": background_prompt,
    }


def generate_images(state: dict[str, Any]) -> dict[str, Any]:
    selected_style = state.get("selected_style", "minimalism")
    design = state.get("design", {})
    pages = state.get("pages", {}).get("pages", [])

    page_images = {
        page.get("name", "page"): _page_images(page=page, design=design, selected_style=selected_style)
        for page in pages
        if page.get("name")
    }

    return {
        "images": {
            "pages": page_images,
            "provider": "prompt_url",
            "style": selected_style,
        }
    }
