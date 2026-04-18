import copy
import hashlib
import json
import re
from typing import Any


DEFAULT_PAGE_SCOPE = [
    {"name": "home", "route": "/home", "goal": "Introduce the brand and drive conversions."},
    {"name": "about", "route": "/about", "goal": "Explain the company story, mission, and team credibility."},
    {"name": "features", "route": "/features", "goal": "Showcase the product capabilities and workflows."},
    {"name": "pricing", "route": "/pricing", "goal": "Present pricing tiers, value, and plan comparisons."},
    {"name": "contact", "route": "/contact", "goal": "Give visitors a clear path to reach out or book a demo."},
]

SECTION_LIBRARY = {
    "navbar": ["links-left-cta-right"],
    "hero": ["split-visual", "centered-stack"],
    "logo_cloud": ["grid-strip"],
    "stats_strip": ["four-up"],
    "feature_grid": ["cards-3up"],
    "feature_split": ["media-left-copy-right"],
    "testimonial_grid": ["three-cards"],
    "pricing_tiers": ["three-tier-highlighted"],
    "faq": ["two-column-accordion"],
    "cta": ["centered-conversion"],
    "footer": ["multi-column-simple"],
}

SECTION_LAYOUT_ROLES = {
    "navbar": "navigation",
    "hero": "hero",
    "logo_cloud": "trust",
    "stats_strip": "trust",
    "feature_grid": "supporting",
    "feature_split": "supporting",
    "testimonial_grid": "trust",
    "pricing_tiers": "conversion",
    "faq": "supporting",
    "cta": "conversion",
    "footer": "footer",
}

DEFAULT_PAGE_SECTIONS = {
    "home": [
        "navbar",
        "hero",
        "logo_cloud",
        "feature_grid",
        "stats_strip",
        "testimonial_grid",
        "pricing_tiers",
        "faq",
        "cta",
        "footer",
    ],
    "about": [
        "navbar",
        "feature_split",
        "stats_strip",
        "testimonial_grid",
        "cta",
        "footer",
    ],
    "features": [
        "navbar",
        "feature_grid",
        "feature_split",
        "logo_cloud",
        "faq",
        "cta",
        "footer",
    ],
    "pricing": [
        "navbar",
        "pricing_tiers",
        "testimonial_grid",
        "faq",
        "cta",
        "footer",
    ],
    "contact": [
        "navbar",
        "feature_split",
        "faq",
        "cta",
        "footer",
    ],
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def titleize_slug(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("-", " ").split())


def build_project_id(prompt: str) -> str:
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:10]
    return f"site-{digest}"


def extract_json_object(raw: str) -> dict[str, Any]:
    if not raw:
        return {}

    candidates = re.findall(r"\{.*\}", raw, re.DOTALL)
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def normalize_style_keywords(style_keywords: Any, prompt: str) -> list[str]:
    if isinstance(style_keywords, list):
        cleaned = [str(item).strip().lower() for item in style_keywords if str(item).strip()]
        if cleaned:
            return cleaned[:5]

    prompt_lower = prompt.lower()
    inferred = []
    for keyword in ["modern", "minimal", "futuristic", "premium", "startup", "portfolio", "saas"]:
        if keyword in prompt_lower:
            inferred.append(keyword)
    return inferred or ["modern", "premium", "clean"]


def build_component_library() -> dict[str, Any]:
    return {
        "allowed_section_types": list(SECTION_LIBRARY.keys()),
        "variants": copy.deepcopy(SECTION_LIBRARY),
        "used_section_types": [],
    }


def build_shared_components(site_name: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nav_links = [{"label": page["name"].title(), "route": page["route"]} for page in pages]
    return [
        {
            "component_id": "shared-navbar",
            "section_type": "navbar",
            "variant": "links-left-cta-right",
            "content_brief": {
                "brand_name": site_name,
                "links": nav_links,
                "primary_cta": {"label": "Book Demo", "route": "/contact"},
            },
        },
        {
            "component_id": "shared-footer",
            "section_type": "footer",
            "variant": "multi-column-simple",
            "content_brief": {
                "brand_name": site_name,
                "links": nav_links,
                "legal_text": f"Copyright {site_name}. All rights reserved.",
            },
        },
    ]


def build_base_design_system() -> dict[str, Any]:
    return {
        "colors": {},
        "typography": {},
        "spacing": {},
        "radii": {},
        "shadows": {},
        "strokes": {},
        "layout": {
            "canvas_width": 1440,
            "container_width": 1200,
            "grid_columns": 12,
            "section_gap": "xl",
        },
    }


def build_figma_sync(project_id: str, site_name: str) -> dict[str, Any]:
    return {
        "project_file_id": project_id,
        "file_name": f"{site_name} - Agentic Designer",
        "sync_strategy": {
            "file_mode": "one_file_per_project",
            "upsert_tokens": True,
            "upsert_components": True,
            "upsert_pages": True,
            "replace_section_instances": True,
        },
    }


def default_page_scope() -> list[dict[str, Any]]:
    pages = []
    for index, page in enumerate(DEFAULT_PAGE_SCOPE):
        pages.append(
            {
                "page_id": f"page-{index + 1}-{page['name']}",
                "name": page["name"],
                "route": page["route"],
                "goal": page["goal"],
                "sections": [],
            }
        )
    return pages


def normalize_planner_pages(raw_pages: Any) -> list[dict[str, Any]]:
    normalized = {page["name"]: dict(page) for page in default_page_scope()}

    if isinstance(raw_pages, list):
        for raw_page in raw_pages:
            if isinstance(raw_page, dict):
                name = slugify(str(raw_page.get("name", "")))
                goal = str(raw_page.get("goal", "")).strip()
            else:
                name = slugify(str(raw_page))
                goal = ""

            if name in normalized and goal:
                normalized[name]["goal"] = goal

    return [normalized[page["name"]] for page in default_page_scope()]


def infer_site_name(prompt: str) -> str:
    words = [word for word in re.findall(r"[A-Za-z0-9]+", prompt) if word]
    if not words:
        return "Agentic Website"
    return " ".join(word.capitalize() for word in words[:3])


def build_initial_site_spec(prompt: str, planner_output: dict[str, Any] | None = None) -> dict[str, Any]:
    planner_output = planner_output or {}
    site_name = str(planner_output.get("site_name") or infer_site_name(prompt)).strip()
    pages = normalize_planner_pages(planner_output.get("pages"))
    style_keywords = normalize_style_keywords(planner_output.get("style_keywords"), prompt)
    project_id = build_project_id(prompt)

    site_spec = {
        "project": {
            "project_id": project_id,
            "prompt": prompt,
            "site_name": site_name,
            "site_type": str(planner_output.get("site_type") or "marketing-site"),
            "style_keywords": style_keywords,
        },
        "pages": pages,
        "design_system": build_base_design_system(),
        "shared_components": build_shared_components(site_name, pages),
        "component_library": build_component_library(),
        "figma_sync": build_figma_sync(project_id, site_name),
    }

    return refresh_component_library_usage(site_spec)


def build_content_brief(section_type: str, page: dict[str, Any], site_spec: dict[str, Any]) -> dict[str, Any]:
    site_name = site_spec["project"]["site_name"]
    style_words = ", ".join(site_spec["project"]["style_keywords"])

    briefs = {
        "navbar": {},
        "hero": {
            "eyebrow": page["name"].title(),
            "headline": f"{site_name} helps teams move faster with confident design systems.",
            "supporting_text": f"A {style_words} website experience built to explain value and drive action.",
            "primary_cta": {"label": "Book Demo", "route": "/contact"},
            "secondary_cta": {"label": "See Pricing", "route": "/pricing"},
        },
        "logo_cloud": {
            "headline": "Trusted by ambitious teams",
            "logos": ["Northstar", "Atlas", "Nova", "Signal", "Orbit"],
        },
        "stats_strip": {
            "headline": "Proof points that build confidence",
            "stats": [
                {"label": "Faster launches", "value": "3x"},
                {"label": "Team adoption", "value": "92%"},
                {"label": "Workflow coverage", "value": "24/7"},
            ],
        },
        "feature_grid": {
            "headline": f"Why teams choose {site_name}",
            "items": [
                "Multi-agent planning for website strategy",
                "Design-system consistency across every page",
                "Structured outputs ready for Figma and code generation",
            ],
        },
        "feature_split": {
            "headline": f"{page['name'].title()} that clarifies the story",
            "supporting_text": page["goal"],
            "media_hint": "abstract product visualization",
            "bullet_points": [
                "Clear narrative structure",
                "Reusable section patterns",
                "Strong visual hierarchy",
            ],
        },
        "testimonial_grid": {
            "headline": "What customers are saying",
            "quotes": [
                "The output feels intentional, not generic.",
                "We finally have consistency across every page.",
                "The workflow gives us strategy and execution in one system.",
            ],
        },
        "pricing_tiers": {
            "headline": "Simple pricing for growing teams",
            "plans": [
                {"name": "Starter", "price": "$49", "highlight": False},
                {"name": "Growth", "price": "$149", "highlight": True},
                {"name": "Scale", "price": "Custom", "highlight": False},
            ],
        },
        "faq": {
            "headline": "Common questions",
            "questions": [
                "How quickly can we launch?",
                "Can the system support multiple pages?",
                "Will this connect to code generation later?",
            ],
        },
        "cta": {
            "headline": "Ready to build your next website with confidence?",
            "supporting_text": "Talk with the team and turn strategy into a polished multi-page experience.",
            "primary_cta": {"label": "Get Started", "route": "/contact"},
        },
        "footer": {},
    }

    return briefs.get(section_type, {"headline": page["goal"]})


def is_valid_section_for_page(section_type: str, page_name: str) -> bool:
    if section_type not in SECTION_LIBRARY:
        return False
    if section_type == "pricing_tiers" and page_name not in {"home", "pricing"}:
        return False
    return True


def normalize_sections(
    page: dict[str, Any],
    site_spec: dict[str, Any],
    raw_sections: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    page_name = page["name"]
    requested = raw_sections if isinstance(raw_sections, list) else []

    section_types = []
    for section in requested:
        section_type = slugify(str(section.get("section_type", "")))
        if is_valid_section_for_page(section_type, page_name):
            section_types.append(section_type)

    if not section_types:
        section_types = list(DEFAULT_PAGE_SECTIONS[page_name])

    if "navbar" not in section_types:
        section_types.insert(0, "navbar")
    if page_name == "home" and "hero" not in section_types:
        section_types.insert(1, "hero")
    if "footer" not in section_types:
        section_types.append("footer")

    filtered = []
    for section_type in section_types:
        if section_type not in filtered and is_valid_section_for_page(section_type, page_name):
            filtered.append(section_type)

    instances = []
    for index, section_type in enumerate(filtered):
        variant = SECTION_LIBRARY[section_type][0]
        raw_section = next(
            (section for section in requested if slugify(str(section.get("section_type", ""))) == section_type),
            {},
        )
        instance = {
            "instance_id": f"{page['page_id']}-{section_type}-{index + 1}",
            "section_type": section_type,
            "variant": str(raw_section.get("variant") or variant),
            "purpose": str(raw_section.get("purpose") or page["goal"]),
            "content_brief": raw_section.get("content_brief")
            if isinstance(raw_section.get("content_brief"), dict)
            else build_content_brief(section_type, page, site_spec),
            "layout_role": SECTION_LAYOUT_ROLES[section_type],
            "depends_on": [],
        }

        if section_type == "navbar":
            instance["depends_on"] = ["shared-navbar"]
            instance["content_brief"] = {}
        if section_type == "footer":
            instance["depends_on"] = ["shared-footer"]
            instance["content_brief"] = {}

        instances.append(instance)

    return instances


def compose_site_pages(site_spec: dict[str, Any], page_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    page_payload = page_payload or {}
    raw_pages = page_payload.get("pages") if isinstance(page_payload, dict) else None

    updated_pages = []
    for page in site_spec["pages"]:
        raw_page = next(
            (
                item
                for item in (raw_pages or [])
                if slugify(str(item.get("name", ""))) == page["name"]
            ),
            {},
        )
        updated_page = dict(page)
        updated_page["sections"] = normalize_sections(
            page,
            site_spec,
            raw_page.get("sections") if isinstance(raw_page, dict) else None,
        )
        updated_pages.append(updated_page)

    site_spec["pages"] = updated_pages
    site_spec["shared_components"] = build_shared_components(site_spec["project"]["site_name"], updated_pages)
    return refresh_component_library_usage(site_spec)


def build_section_layout(section: dict[str, Any]) -> dict[str, Any]:
    layout_map = {
        "navbar": {
            "container": "full-bleed",
            "grid_columns": 12,
            "content_span": "12",
            "alignment": "center",
            "padding_block": "md",
        },
        "hero": {
            "container": "wide",
            "grid_columns": 12,
            "content_span": "6/6",
            "alignment": "left",
            "padding_block": "3xl",
        },
        "logo_cloud": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "12",
            "alignment": "center",
            "padding_block": "xl",
        },
        "stats_strip": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "3/3/3/3",
            "alignment": "center",
            "padding_block": "xl",
        },
        "feature_grid": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "4/4/4",
            "alignment": "left",
            "padding_block": "2xl",
        },
        "feature_split": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "6/6",
            "alignment": "left",
            "padding_block": "2xl",
        },
        "testimonial_grid": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "4/4/4",
            "alignment": "left",
            "padding_block": "2xl",
        },
        "pricing_tiers": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "4/4/4",
            "alignment": "center",
            "padding_block": "2xl",
        },
        "faq": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "6/6",
            "alignment": "left",
            "padding_block": "2xl",
        },
        "cta": {
            "container": "container",
            "grid_columns": 12,
            "content_span": "8",
            "alignment": "center",
            "padding_block": "2xl",
        },
        "footer": {
            "container": "full-bleed",
            "grid_columns": 12,
            "content_span": "12",
            "alignment": "left",
            "padding_block": "xl",
        },
    }

    return layout_map[section["section_type"]]


def apply_layout_metadata(site_spec: dict[str, Any]) -> dict[str, Any]:
    for page in site_spec["pages"]:
        for section in page["sections"]:
            section["layout"] = build_section_layout(section)
    return site_spec


def _palette_for_keywords(style_keywords: list[str]) -> dict[str, str]:
    keywords = set(style_keywords)
    if {"futuristic", "ai", "startup"} & keywords:
        return {
            "primary": "#4F46E5",
            "secondary": "#06B6D4",
            "accent": "#22C55E",
            "background": "#0F172A",
            "surface": "#111827",
            "text": "#E5E7EB",
            "muted": "#94A3B8",
            "border": "#334155",
        }
    if {"portfolio"} & keywords:
        return {
            "primary": "#0F766E",
            "secondary": "#F59E0B",
            "accent": "#EA580C",
            "background": "#FFFBF5",
            "surface": "#FFFFFF",
            "text": "#1F2937",
            "muted": "#6B7280",
            "border": "#E5E7EB",
        }
    return {
        "primary": "#2563EB",
        "secondary": "#0EA5E9",
        "accent": "#14B8A6",
        "background": "#F8FAFC",
        "surface": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#475569",
        "border": "#CBD5E1",
    }


def build_complete_design_system(site_spec: dict[str, Any], theme_output: dict[str, Any] | None = None) -> dict[str, Any]:
    theme_output = theme_output or {}
    colors = _palette_for_keywords(site_spec["project"]["style_keywords"])
    colors.update(theme_output.get("colors", {}))

    design_system = {
        "colors": colors,
        "typography": {
            "font_families": {
                "display": theme_output.get("typography", {}).get("font_families", {}).get("display", "Space Grotesk"),
                "body": theme_output.get("typography", {}).get("font_families", {}).get("body", "Inter"),
            },
            "sizes": {
                "display": "72/80",
                "h1": "56/64",
                "h2": "40/48",
                "h3": "32/40",
                "body_lg": "20/32",
                "body_md": "16/28",
                "body_sm": "14/24",
            },
            "weights": {"regular": 400, "medium": 500, "semibold": 600, "bold": 700},
            "line_heights": {"tight": 1.1, "base": 1.5, "relaxed": 1.7},
        },
        "spacing": {"xs": 8, "sm": 12, "md": 16, "lg": 24, "xl": 40, "2xl": 64, "3xl": 96},
        "radii": {"sm": 8, "md": 16, "lg": 24, "pill": 999},
        "shadows": {
            "subtle": "0 6px 18px rgba(15, 23, 42, 0.08)",
            "soft": "0 14px 40px rgba(15, 23, 42, 0.12)",
        },
        "strokes": {"subtle": f"1px solid {colors['border']}"},
        "layout": {
            "canvas_width": 1440,
            "container_width": 1200,
            "grid_columns": 12,
            "section_gap": "xl",
        },
    }

    site_spec["design_system"] = design_system
    return site_spec


def refresh_component_library_usage(site_spec: dict[str, Any]) -> dict[str, Any]:
    used = set()
    for page in site_spec.get("pages", []):
        for section in page.get("sections", []):
            used.add(section["section_type"])
    for component in site_spec.get("shared_components", []):
        used.add(component["section_type"])
    site_spec["component_library"]["used_section_types"] = sorted(used)
    return site_spec
