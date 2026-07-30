import json
import re
from pydantic import BaseModel, Field
from agents.llm import qwen_llm
from langchain_core.messages import SystemMessage, HumanMessage
from schema.asset import (
    AssetOutput,
    AssetPriority,
    AssetRequirement,
    AssetType,
    SourceStrategy,
)

class RevisedPromptResponse(BaseModel):
    revised_prompt: str = Field(..., description="The rewritten prompt incorporating the user's edit request while keeping the core subject intact.")

class AssetAgent:
    """Agent responsible for intelligent asset generation and editing."""
    
    def __init__(self):
        self.llm = qwen_llm()

    def _safe_asset_id(self, *parts: str) -> str:
        value = "_".join(part for part in parts if part)
        value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
        return value or "website_asset"

    def _fallback_plan_assets(self, page_design_output) -> AssetOutput:
        assets: list[AssetRequirement] = []
        asset_keywords = {
            "hero",
            "showcase",
            "gallery",
            "visual",
            "image",
            "parallax",
            "story",
            "product",
            "interior",
            "feature",
            "background",
            "reveal",
        }

        for page in page_design_output.pages:
            for section in page.sections:
                section_text = " ".join([
                    section.section_name,
                    section.section_goal,
                    section.layout,
                    section.visual_style,
                    " ".join(section.animations),
                ]).lower()

                if not any(keyword in section_text for keyword in asset_keywords):
                    continue

                asset_id = self._safe_asset_id(page.page_name, section.section_name)
                prompt = (
                    f"High-quality website visual asset for {page.page_name}, "
                    f"{section.section_name}. Section goal: {section.section_goal}. "
                    f"Visual style: {section.visual_style}. Match the page design and avoid text in the image."
                )
                assets.append(
                    AssetRequirement(
                        asset_id=asset_id,
                        page_name=page.page_name,
                        section_name=section.section_name,
                        purpose=section.section_goal,
                        asset_type=AssetType.IMAGE,
                        priority=AssetPriority.HIGH if "hero" in section_text else AssetPriority.MEDIUM,
                        source_strategy=SourceStrategy.GENERATE,
                        generation_required=True,
                        prompt=prompt,
                        negative_prompt="text, watermark, logo artifacts, distorted UI, low quality",
                        style_keywords=[section.visual_style],
                        animation_required=False,
                        animation_description=None,
                        width=1920,
                        height=1080,
                        format=".png",
                        output_filename=f"{asset_id}.png",
                    )
                )

        return AssetOutput(
            project_style="Generated from page design",
            design_theme=page_design_output.global_rules.transition_style,
            assets=assets,
        )

    async def plan_assets(self, page_design_output) -> AssetOutput:
        """
        Plan visual asset slots before page code is generated.
        The code agent uses these asset_id values as exact data-asset-id targets.
        """
        system_prompt = (
            "You are an expert website asset planner. Plan only the visual assets "
            "that a frontend UI needs: hero images, product visuals, storytelling "
            "frames, parallax visuals, section backgrounds, closeups, icons, logos, "
            "or image assets. Do not create unnecessary assets for text-only sections. "
            "Return a valid structured AssetOutput."
        )
        user_message = (
            "Create an asset plan for this page design. Each asset_id must be stable, "
            "lowercase snake_case, and clearly tied to a page section. Include prompts "
            "that can be used directly by an image generator.\n\n"
            f"{page_design_output.model_dump_json(indent=2)}"
        )

        try:
            structured_llm = self.llm.with_structured_output(AssetOutput)
            response = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ])
            return response
        except Exception as exc:
            print(f"AssetAgent planning failed, using fallback plan: {exc}")
            return self._fallback_plan_assets(page_design_output)
        
    async def process_edit_request(self, original_prompt: str, edit_request: str) -> str:
        """
        Takes the original image prompt and a user's edit request (e.g., 'make it darker'),
        and rewrites the prompt to apply the edit.
        """
        system_prompt = (
            "You are an expert AI image prompt engineer. Your job is to take an original image prompt "
            "and a user's requested edit, and rewrite the prompt so that it applies the edit seamlessly. "
            "Keep the core subject and style intact unless the edit specifically requests changing them. "
            "Return ONLY the revised prompt as a plain string, optimizing it for text-to-image models."
        )
        
        user_message = (
            f"Original Prompt: {original_prompt}\n"
            f"User's Edit Request: {edit_request}\n\n"
            f"Rewrite the prompt to apply this edit."
        )
        
        try:
            llm_with_structure = self.llm.with_structured_output(RevisedPromptResponse)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            response = await llm_with_structure.ainvoke(messages)
            return response.revised_prompt
        except Exception as e:
            print(f"AssetAgent edit failed: {e}")
            # Fallback to just appending the request if generation fails
            return f"{original_prompt}, {edit_request}"
