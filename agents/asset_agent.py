"""
AssetAgent — Pure Asset Planning Agent.

Responsibilities:
- Plans visual assets from the full pipeline context.
- Returns an AssetOutput (requirements only, no generation).
- Never decides animations, parallax, or motion effects.
- Never generates images.
"""
from __future__ import annotations

import json
import re
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from agents.llm import gemini_flash_llm
from pipeline_utils import resilient_ainvoke, parse_model_json
from schema.asset import (
    AssetOutput,
    AssetPriority,
    AssetRequirement,
    AssetType,
    SourceStrategy,
)

logger = logging.getLogger(__name__)


class AssetAgent:
    """Pure Asset Planning Agent.

    Plans which visual assets the website needs based on the full pipeline
    context (architecture, research, design system, and page blueprints).
    Does NOT generate images — that is the GenerationAgent's job.
    """

    def __init__(self):
        self.llm = gemini_flash_llm()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_asset_id(self, *parts: str) -> str:
        value = "_".join(part for part in parts if part)
        value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
        return value or "website_asset"

    def _fallback_plan_assets(self, page_design_output) -> AssetOutput:
        """Rule-based fallback when LLM planning fails."""
        assets: list[AssetRequirement] = []

        hero_keywords    = {"hero", "banner", "header", "showcase", "landing"}
        product_keywords = {"gallery", "product", "portfolio", "collection", "work"}
        bg_keywords      = {"background", "parallax", "reveal", "story", "interior"}
        visual_keywords  = {"visual", "image", "feature", "closeup", "section"}

        all_visual_keywords = (
            hero_keywords | product_keywords | bg_keywords | visual_keywords
        )

        for page in page_design_output.pages:
            for section in page.sections:
                section_text = " ".join([
                    section.section_name,
                    section.section_goal,
                    section.layout,
                    section.visual_style,
                ]).lower()

                if not any(kw in section_text for kw in all_visual_keywords):
                    continue

                # Determine priority based on section type
                if any(kw in section_text for kw in hero_keywords):
                    priority = AssetPriority.HIGH
                elif any(kw in section_text for kw in product_keywords):
                    priority = AssetPriority.MEDIUM
                elif any(kw in section_text for kw in bg_keywords):
                    priority = AssetPriority.MEDIUM
                else:
                    priority = AssetPriority.LOW

                asset_id = self._safe_asset_id(page.page_name, section.section_name)
                prompt = (
                    f"High-quality website visual for '{page.page_name}' page, "
                    f"'{section.section_name}' section. "
                    f"Goal: {section.section_goal}. "
                    f"Visual style: {section.visual_style}. "
                    "Photorealistic, professional, no text or watermarks."
                )

                assets.append(
                    AssetRequirement(
                        asset_id=asset_id,
                        page_name=page.page_name,
                        section_name=section.section_name,
                        purpose=section.section_goal,
                        asset_type=AssetType.IMAGE,
                        priority=priority,
                        source_strategy=SourceStrategy.GENERATE,
                        generation_required=True,
                        prompt=prompt,
                        negative_prompt=(
                            "text, watermark, logo, UI artifacts, distortion, "
                            "low quality, blurry, animation, motion blur"
                        ),
                        style_keywords=[section.visual_style],
                        animation_required=False,
                        animation_description=None,
                        width=1920,
                        height=1080,
                        output_filename=f"{asset_id}.png",
                    )
                )

        return AssetOutput(
            project_style="Fallback from page design",
            design_theme=getattr(
                getattr(page_design_output, "global_rules", None),
                "transition_style",
                "modern"
            ),
            assets=assets,
        )

    # ------------------------------------------------------------------
    # Main planning method
    # ------------------------------------------------------------------

    async def plan_assets(
        self,
        page_design_output,
        architect_output=None,
        research_output=None,
        design_system_output=None,
        page_code_output=None,
    ) -> AssetOutput:
        """
        Plan all visual asset requirements for the website.

        Uses the full pipeline context to determine which assets are needed,
        their priorities, dimensions, prompts, and source strategies.

        Returns:
            AssetOutput — list of AssetRequirement objects only.
            Does NOT generate any images.
        """
        schema_json = json.dumps(AssetOutput.model_json_schema(), indent=2)

        system_prompt = f"""You are an expert visual asset planner for AI-generated websites.

Your ONLY responsibility is to decide which visual assets the website requires.

Do NOT generate images.
Do NOT plan animations, motion effects, parallax, GSAP, Framer Motion, or any frontend effects. Those belong to the MotionAgent.

Plan only meaningful visual assets that represent real-world subjects required by the website.

Examples include:
- Products
- Vehicles
- Buildings
- Interiors
- Architecture
- Landscapes
- Food
- Consumer devices
- Furniture
- Industrial equipment
- Fashion items
- Real people
- Physical objects

Do NOT create image assets for:
- Abstract gradients
- Mesh backgrounds
- Decorative blobs
- Glassmorphism effects
- UI backgrounds
- Textures
- Light streaks
- Neon effects
- CSS decorations
- Generic abstract artwork

These should be created using CSS, SVG, or frontend code.

For every GENERATE asset, create a production-quality image generation prompt that produces a highly realistic photograph or photorealistic render.

Each prompt should naturally include:
- Main subject
- Environment
- Camera angle
- Professional lighting
- Realistic materials and textures
- Composition
- High detail
- Photorealistic quality

Avoid mentioning text, UI elements, logos, or watermarks unless explicitly requested.

RULES:
1. Each asset_id must be stable lowercase snake_case tied to page + section
2. For every GENERATE asset, write a production-ready prompt that describes a realistic scene or object. The prompt should naturally specify the subject, environment, composition, camera perspective, professional lighting, realistic materials, and photorealistic quality suitable for high-end commercial websites.
3. Set generation_required=false for icon_library and logo_library
4. Dimensions: hero=1920x1080, background=1920x1080, product=800x600, icon=64x64, logo=400x200, square=1024x1024
5. Never include motion, animation, or parallax decisions
6. Never generate prompts for abstract art, fantasy scenes, cartoon illustrations, glowing backgrounds, decorative graphics, UI mockups, screenshots, gradients, or placeholder images unless the website explicitly requires them.

Return ONLY valid JSON matching this schema:
{schema_json}"""

        # Build rich context from all available pipeline outputs
        context_parts = []

        if architect_output:
            try:
                context_parts.append(
                    f"=== ARCHITECTURE ===\n{architect_output.model_dump_json(indent=2)}"
                )
            except Exception:
                pass

        if research_output:
            try:
                context_parts.append(
                    f"=== RESEARCH ===\n{research_output.model_dump_json(indent=2)}"
                )
            except Exception:
                pass

        if design_system_output:
            try:
                context_parts.append(
                    f"=== DESIGN SYSTEM ===\n{design_system_output.model_dump_json(indent=2)}"
                )
            except Exception:
                pass

        if page_design_output:
            try:
                context_parts.append(
                    f"=== PAGE BLUEPRINTS ===\n{page_design_output.model_dump_json(indent=2)}"
                )
            except Exception:
                pass

        if page_code_output:
            try:
                # Only include filenames to inspect data-asset-id placeholders
                filenames = list(getattr(page_code_output, "files", {}).keys())
                context_parts.append(
                    f"=== GENERATED CODE FILES (for placeholder inspection) ===\n"
                    f"{json.dumps(filenames, indent=2)}"
                )
            except Exception:
                pass

        user_message = (
            "Plan all visual asset requirements for this website based on the context below.\n"
            "Return a valid JSON AssetOutput.\n\n"
            + "\n\n".join(context_parts)
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        try:
            response = await resilient_ainvoke(
                self.llm, messages, "asset_planning"
            )
            raw = response.content if hasattr(response, "content") else str(response)
            result = parse_model_json(AssetOutput, raw)
            logger.info(
                f"AssetAgent planned {len(result.assets)} assets successfully"
            )
            return result
        except Exception as exc:
            logger.warning(
                f"AssetAgent LLM planning failed, using fallback: {exc}"
            )
            return self._fallback_plan_assets(page_design_output)
