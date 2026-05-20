import json
import logging
import os
from typing import Any

from pydantic import BaseModel, Field

try:
    from .llm import PLANNING_MODEL, invoke_structured_model
except ImportError:
    from agents.llm import PLANNING_MODEL, invoke_structured_model


logger = logging.getLogger(__name__)

VALID_STYLES = {
    "glassmorphism",
    "skeuomorphism",
    "claymorphism",
    "minimalism",
    "liquid_glass",
    "neo_brutalism",
}

STYLE_GUIDANCE = {
    "glassmorphism": {
        "visuals": "frosted glass panels, blur, translucent layering, dark backgrounds, neon or cool accent lighting",
        "motion": "smooth fades, soft parallax, fluid transitions",
    },
    "skeuomorphism": {
        "visuals": "realistic materials, depth, tactile controls, shadowed physical surfaces",
        "motion": "press and release motion, tactile easing, restrained realism",
    },
    "claymorphism": {
        "visuals": "soft 3D blobs, pastel colors, rounded shapes, inflated surfaces",
        "motion": "bouncy spring motion, playful easing, floating elements",
    },
    "minimalism": {
        "visuals": "clean typography, strong whitespace, restrained color, crisp hierarchy",
        "motion": "subtle fades, minimal transforms, no visual noise",
    },
    "liquid_glass": {
        "visuals": "visionOS-style translucent surfaces, saturated blur, liquid highlights, morphing forms",
        "motion": "fluid morphing transitions, depth-rich movement, elegant motion continuity",
    },
    "neo_brutalism": {
        "visuals": "hard borders, flat high-contrast colors, raw typography, offset shadows",
        "motion": "sharp snap transitions, abrupt but intentional movement, glitch accents",
    },
}


def _dump_model(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class PageGroups(BaseModel):
    marketing_pages: list[str] = Field(default_factory=list)
    service_pages: list[str] = Field(default_factory=list)
    catalog_pages: list[str] = Field(default_factory=list)
    auth_pages: list[str] = Field(default_factory=list)
    dashboard_pages: list[str] = Field(default_factory=list)
    resource_pages: list[str] = Field(default_factory=list)
    docs_pages: list[str] = Field(default_factory=list)
    support_pages: list[str] = Field(default_factory=list)
    legal_pages: list[str] = Field(default_factory=list)


class SitePlan(BaseModel):
    page_groups: PageGroups
    style: str
    layout: dict[str, list[str]] = Field(default_factory=dict)
    assets: list[str] = Field(default_factory=list)


class Palette(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text: str


class Typography(BaseModel):
    heading: str
    body: str


class AssetDirection(BaseModel):
    icons: str
    hero: str
    background: str


class DesignSystem(BaseModel):
    style_family: str
    mode: str
    brand_mood: list[str] = Field(default_factory=list)
    palette: Palette
    typography: Typography
    spacing: list[int] = Field(default_factory=list)
    radius: list[int] = Field(default_factory=list)
    shadows: str
    surface_style: str
    motion: str
    assets: AssetDirection


class UISection(BaseModel):
    type: str
    variant: str
    layout: str
    motion: str


class PlannedPage(BaseModel):
    name: str
    route: str
    type: str
    goal: str
    sections: list[str] = Field(default_factory=list)
    ui_sections: list[UISection] = Field(default_factory=list)
    image_prompt: str = ""
    requires_generated_visual: bool = False


class SiteSpecification(BaseModel):
    plan: SitePlan
    design: DesignSystem
    pages: list[PlannedPage] = Field(default_factory=list)


SYSTEM_PROMPT = """
You are the master website planning agent for a production-grade AI website generator.

You convert a user request into a complete premium website, app, or tool specification.

Requirements:
- Think like a senior product designer, creative director, UX architect, and frontend lead.
- Produce realistic information architecture for modern websites.
- Make the output premium, coherent, and buildable.
- Use dark mode only if it matches the request or improves the concept.
- Prefer premium modern layouts, bold visual direction, strong hierarchy, and motion-aware sections.
- Every page must have a clear purpose and a logical route.
- Every page must include UI sections that a frontend engineer can directly implement.
- Use section variants that can support premium animation with GSAP, Framer Motion, and React Three Fiber when appropriate.
- Keep the page count practical for an MVP, usually 3 to 8 pages.
- If the request is for a tool, calculator, editor, dashboard, game, or utility, prioritize the actual usable interface over marketing pages.
- Use snake_case names for page names and section types.
- Home page route must be "/".
- Other routes must begin with "/".
- The selected style is mandatory and must drive the full design system, section variants, and motion language.
"""


def _normalize_selected_style(selected_style: str | None) -> str:
    style = str(selected_style or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not style:
        raise ValueError("selected_style is required")
    if style not in VALID_STYLES:
        allowed = ", ".join(sorted(VALID_STYLES))
        raise ValueError(f"selected_style must be one of: {allowed}")
    return style


def _normalize_page_name(name: str) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_route(route: str, page_name: str) -> str:
    cleaned = str(route).strip()
    if not cleaned:
        return "/" if page_name in {"home", "landing"} else f"/{page_name}"
    if cleaned == "/":
        return "/"
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned


def _normalize_sections(sections: list[str]) -> list[str]:
    normalized = []
    seen = set()

    for section in sections:
        section_name = _normalize_page_name(section)
        if section_name and section_name not in seen:
            seen.add(section_name)
            normalized.append(section_name)

    return normalized[:7]


def _page_requires_generated_visual(page_type: str, sections: list[str]) -> bool:
    normalized_type = str(page_type).lower()
    section_set = {str(section).lower() for section in sections}
    visual_sections = {
        "hero",
        "showcase",
        "banner",
        "gallery",
        "demo_preview",
        "product_detail",
        "culture",
        "featured_posts",
        "featured_technology",
        "mission",
    }
    if "marketing" in normalized_type:
        return True
    return bool(section_set & visual_sections)


def _normalize_site_spec(spec: SiteSpecification) -> SiteSpecification:
    route_seen = set()
    normalized_pages: list[PlannedPage] = []

    for raw_page in spec.pages[:8]:
        page_name = _normalize_page_name(raw_page.name)
        if not page_name:
            continue

        route = _normalize_route(raw_page.route, page_name)
        if route in route_seen:
            continue

        route_seen.add(route)
        normalized_sections = _normalize_sections(raw_page.sections)

        normalized_ui_sections = []
        for ui_section in raw_page.ui_sections:
            section_type = _normalize_page_name(ui_section.type)
            if section_type not in normalized_sections:
                continue

            normalized_ui_sections.append(
                UISection(
                    type=section_type,
                    variant=str(ui_section.variant).strip() or "premium_default",
                    layout=str(ui_section.layout).strip() or "stack",
                    motion=str(ui_section.motion).strip() or "fade_up",
                )
            )

        missing_ui_sections = [
            section
            for section in normalized_sections
            if section not in {item.type for item in normalized_ui_sections}
        ]

        for section in missing_ui_sections:
            normalized_ui_sections.append(
                UISection(
                    type=section,
                    variant="premium_default",
                    layout="stack",
                    motion="fade_up",
                )
            )

        normalized_pages.append(
            PlannedPage(
                name=page_name,
                route="/" if page_name in {"home", "landing"} else route,
                type=str(raw_page.type).strip() or "marketing",
                goal=str(raw_page.goal).strip() or "present content clearly",
                sections=normalized_sections or ["navbar", "hero", "content", "footer"],
                ui_sections=normalized_ui_sections,
                image_prompt=str(raw_page.image_prompt).strip(),
                requires_generated_visual=bool(raw_page.requires_generated_visual)
                or _page_requires_generated_visual(
                    str(raw_page.type).strip() or "marketing",
                    normalized_sections or ["navbar", "hero", "content", "footer"],
                ),
            )
        )

    if not normalized_pages:
        raise ValueError("Planner returned no usable pages")

    spec.pages = normalized_pages
    return spec


def _site_spec_to_state(spec: SiteSpecification) -> dict[str, Any]:
    spec = _normalize_site_spec(spec)
    design_motion = str(spec.design.motion).strip()
    design_style = str(spec.design.style_family).strip()

    pages_payload = {
        "pages": [
            {
                "name": page.name,
                "route": page.route,
                "type": page.type,
                "goal": page.goal,
                "sections": page.sections,
                "style": design_style,
                "animation_intent": " | ".join(
                    dict.fromkeys(
                        [
                            str(section.motion).strip()
                            for section in page.ui_sections
                            if str(section.motion).strip()
                        ]
                    )
                )
                or design_motion,
                "image_prompt": page.image_prompt,
                "requires_generated_visual": page.requires_generated_visual,
            }
            for page in spec.pages
        ]
    }

    ui_payload = {
        "pages": [
            {
                "name": page.name,
                "route": page.route,
                "ui_sections": [_dump_model(section) for section in page.ui_sections],
            }
            for page in spec.pages
        ]
    }

    return {
        "plan": _dump_model(spec.plan),
        "design": _dump_model(spec.design),
        "pages": pages_payload,
        "ui": ui_payload,
    }


def _fallback_palette(style: str) -> Palette:
    palettes = {
        "glassmorphism": Palette(
            primary="#22d3ee",
            secondary="#818cf8",
            accent="#d3ff72",
            background="#020617",
            surface="rgba(15, 23, 42, 0.72)",
            text="#f8fafc",
        ),
        "skeuomorphism": Palette(
            primary="#58c7f3",
            secondary="#d6c7ad",
            accent="#f3d27a",
            background="#07111f",
            surface="#111827",
            text="#f8fafc",
        ),
        "claymorphism": Palette(
            primary="#fb7185",
            secondary="#93c5fd",
            accent="#fde68a",
            background="#fff7ed",
            surface="#fed7aa",
            text="#1f2937",
        ),
        "minimalism": Palette(
            primary="#111827",
            secondary="#6b7280",
            accent="#2563eb",
            background="#f8fafc",
            surface="#ffffff",
            text="#111827",
        ),
        "liquid_glass": Palette(
            primary="#7dd3fc",
            secondary="#c084fc",
            accent="#f0abfc",
            background="#030712",
            surface="rgba(17, 24, 39, 0.68)",
            text="#f9fafb",
        ),
        "neo_brutalism": Palette(
            primary="#0f172a",
            secondary="#f97316",
            accent="#facc15",
            background="#f8fafc",
            surface="#ffffff",
            text="#0f172a",
        ),
    }
    return palettes[style]


def _fallback_site_spec(prompt: str, selected_style: str) -> SiteSpecification:
    style_guidance = STYLE_GUIDANCE[selected_style]
    palette = _fallback_palette(selected_style)

    prompt_lower = prompt.lower()
    is_calculator = any(
        token in prompt_lower
        for token in ["calculator", "calculation", "calculate", "calculations"]
    )

    if is_calculator:
        pages = [
            PlannedPage(
                name="calculator",
                route="/",
                type="tool",
                goal="provide a usable calculator interface for common calculations",
                sections=[
                    "calculator_workspace",
                    "calculation_modes",
                    "history",
                    "reference",
                    "settings",
                ],
                ui_sections=[
                    UISection(
                        type="calculator_workspace",
                        variant=f"{selected_style}_scientific_calculator",
                        layout="split_tool_surface",
                        motion="tactile_press_feedback",
                    ),
                    UISection(
                        type="calculation_modes",
                        variant="mode_tabs",
                        layout="horizontal",
                        motion="fade_up",
                    ),
                    UISection(
                        type="history",
                        variant="calculation_tape",
                        layout="side_panel",
                        motion="slide_in",
                    ),
                    UISection(
                        type="reference",
                        variant="formula_shortcuts",
                        layout="grid",
                        motion="cascade_cards",
                    ),
                    UISection(
                        type="settings",
                        variant="precision_controls",
                        layout="compact_panel",
                        motion="fade_up",
                    ),
                ],
                image_prompt="",
                requires_generated_visual=False,
            )
        ]

        return SiteSpecification(
            plan=SitePlan(
                page_groups=PageGroups(
                    dashboard_pages=["calculator"],
                ),
                style=selected_style,
                layout={page.name: page.sections for page in pages},
                assets=["self-contained calculator UI", "inline icons", "tailwind utilities"],
            ),
            design=DesignSystem(
                style_family=selected_style,
                mode="dark" if selected_style not in {"minimalism", "neo_brutalism", "claymorphism"} else "light",
                brand_mood=["precise", "usable", "tactile"],
                palette=palette,
                typography=Typography(heading="Inter, ui-sans-serif", body="Inter, ui-sans-serif"),
                spacing=[3, 4, 6, 8, 12, 16],
                radius=[4, 8, 12, 18],
                shadows="tactile control depth with clear pressed and idle states",
                surface_style=style_guidance["visuals"],
                motion=style_guidance["motion"],
                assets=AssetDirection(
                    icons="inline calculator and operation symbols",
                    hero="not needed for the tool interface",
                    background="subtle workspace background that does not distract from controls",
                ),
            ),
            pages=pages,
        )

    pages = [
        PlannedPage(
            name="home",
            route="/",
            type="marketing",
            goal="present the core offer and convert visitors",
            sections=["navbar", "hero", "features", "cta", "footer"],
            ui_sections=[
                UISection(type="navbar", variant=f"{selected_style}_nav", layout="horizontal", motion="fade_down"),
                UISection(type="hero", variant=f"{selected_style}_hero", layout="centered", motion="stagger_reveal"),
                UISection(type="features", variant="bento_grid", layout="grid", motion="cascade_cards"),
                UISection(type="cta", variant="focused_panel", layout="stack", motion="scale_in"),
                UISection(type="footer", variant="compact", layout="horizontal", motion="fade_up"),
            ],
            image_prompt=f"{prompt}, premium {selected_style} hero visual",
            requires_generated_visual=True,
        ),
        PlannedPage(
            name="technology",
            route="/technology",
            type="marketing",
            goal="explain the product technology and differentiators",
            sections=["navbar", "hero", "capabilities", "process", "footer"],
            ui_sections=[
                UISection(type="navbar", variant=f"{selected_style}_nav", layout="horizontal", motion="fade_down"),
                UISection(type="hero", variant="technical_intro", layout="two_column", motion="fade_up"),
                UISection(type="capabilities", variant="feature_matrix", layout="grid", motion="cascade_cards"),
                UISection(type="process", variant="timeline", layout="stack", motion="stagger_reveal"),
                UISection(type="footer", variant="compact", layout="horizontal", motion="fade_up"),
            ],
            image_prompt=f"{prompt}, product technology interface",
            requires_generated_visual=True,
        ),
        PlannedPage(
            name="pricing",
            route="/pricing",
            type="marketing",
            goal="compare plans and drive signup",
            sections=["navbar", "hero", "pricing_cards", "faq", "footer"],
            ui_sections=[
                UISection(type="navbar", variant=f"{selected_style}_nav", layout="horizontal", motion="fade_down"),
                UISection(type="hero", variant="pricing_intro", layout="centered", motion="fade_up"),
                UISection(type="pricing_cards", variant="three_tier", layout="grid", motion="cascade_cards"),
                UISection(type="faq", variant="accordion_style", layout="stack", motion="fade_up"),
                UISection(type="footer", variant="compact", layout="horizontal", motion="fade_up"),
            ],
            image_prompt=f"{prompt}, premium pricing page background",
            requires_generated_visual=False,
        ),
    ]

    return SiteSpecification(
        plan=SitePlan(
            page_groups=PageGroups(
                marketing_pages=["home", "technology", "pricing"],
            ),
            style=selected_style,
            layout={page.name: page.sections for page in pages},
            assets=["self-contained jsx", "tailwind utilities", "inline visual treatments"],
        ),
        design=DesignSystem(
            style_family=selected_style,
            mode="dark" if selected_style not in {"minimalism", "neo_brutalism", "claymorphism"} else "light",
            brand_mood=["premium", "focused", "modern"],
            palette=palette,
            typography=Typography(heading="Inter, ui-sans-serif", body="Inter, ui-sans-serif"),
            spacing=[4, 6, 8, 12, 16, 24],
            radius=[4, 8, 16, 24],
            shadows="style-specific depth with restrained premium contrast",
            surface_style=style_guidance["visuals"],
            motion=style_guidance["motion"],
            assets=AssetDirection(
                icons="inline geometric icons",
                hero="self-contained generated visual treatment",
                background="CSS gradients, grids, and layered surfaces",
            ),
        ),
        pages=pages,
    )


def planner(prompt: str, selected_style: str) -> dict[str, Any]:
    normalized_style = _normalize_selected_style(selected_style)
    style_guidance = STYLE_GUIDANCE[normalized_style]

    planner_mode = os.getenv("PLANNER_MODE", "llm").strip().lower()
    if planner_mode in {"fallback", "static", "deterministic"}:
        logger.info("Using deterministic planner fallback")
        state_payload = _site_spec_to_state(_fallback_site_spec(prompt, normalized_style))
        state_payload["plan"]["style"] = normalized_style
        return state_payload

    planning_prompt = f"""
User Request:
{prompt}

Selected Design Style:
{normalized_style}

Style-Specific Visual Direction:
- Visual language: {style_guidance["visuals"]}
- Motion language: {style_guidance["motion"]}

Return a complete website specification with:
- plan
- design
- pages

Rules:
- Keep the website practical but premium.
- The output must strongly and consistently express the selected design style.
- Set plan.style to the selected style name or a close style-family derivative of it.
- Make the design palette, surface system, typography, motion, and ui_sections consistent with the selected style.
- Every page must include both sections and ui_sections.
- ui_sections must align one-to-one with the page sections whenever possible.
- Favor premium animation-ready variants.
- Include shared navigation and footer patterns across public pages.
- Each page must include an image_prompt for hero or background image generation.
- Set requires_generated_visual=true for pages that need image-led premium presentation.
- For SaaS, startup, AI, gaming, or futuristic products, bias toward bold motion and high-contrast premium composition.
- For trust-heavy categories like finance, law, healthcare, or B2B enterprise, keep the design more restrained and trustworthy.
"""

    try:
        spec = invoke_structured_model(
            prompt=planning_prompt,
            schema=SiteSpecification,
            system_prompt=SYSTEM_PROMPT,
            model_name=PLANNING_MODEL,
            temperature=0.3,
            max_attempts=1,
            max_completion_tokens=4096,
        )
    except Exception as exc:
        if os.getenv("ALLOW_PLANNER_FALLBACK", "false").lower() not in {"1", "true", "yes", "on"}:
            raise
        logger.warning("Planner LLM failed; using deterministic fallback: %s", exc)
        spec = _fallback_site_spec(prompt, normalized_style)

    logger.info("Merged planning spec generated with %s pages", len(spec.pages))
    state_payload = _site_spec_to_state(spec)
    state_payload["plan"]["style"] = normalized_style

    if os.getenv("PRINT_AGENT_JSON", "false").lower() in {"1", "true", "yes", "on"}:
        print("[planner] validated json output:", flush=True)
        print(json.dumps(state_payload, indent=2), flush=True)

    return state_payload
