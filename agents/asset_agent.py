from schema.asset import (
    AssetOutput,
    AssetPriority,
    AssetRequirement,
    AssetType,
    SourceStrategy,
)
from schema.page_d import PageDesignOutput
from agents.json_utils import extract_json_object, load_model_json

from agents.llm import reason_llm, deepseek_llm
from agents.resilient_llm import resilient_ainvoke

from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)
import os
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an elite Digital Asset Planner.

Your responsibility is to determine all assets
required by a website.

You do NOT generate assets.

You do NOT download assets.

You do NOT create files.

You only create an asset plan.



- generate
- internet
- icon_library
- logo_library
- client_provided

Determine:

- essential images
- essential videos only when the page explicitly needs media playback
- icons
- diagrams
- illustrations
- logos
- lottie animations only when the page explicitly needs reusable animated UI media
- section background assets only when they materially improve the page

For every asset define:

- asset id
- page
- section
- purpose
- asset type
- priority
- source strategy
- prompt
- dimensions
- format

Use the Page Design output.



For generated assets create production-ready prompts.

Prompts must include:

- subject
- composition
- camera angle
- lighting
- atmosphere
- color palette
- visual style
- quality level
- rendering style

Prompts should be directly usable by:

- Flux
- Pollinations
- SDXL
- Grok Image

Avoid vague prompts.

Every generated asset must have a highly detailed prompt.

Asset volume rules:

- Create only assets that the final UI must visibly use.
- Maximum 6 generated assets per page.
- Prefer 3 to 5 generated assets per page for normal pages.
- Do not generate one asset for every card, icon, button, badge, or decorative element.
- Use icon_library for icons and UI symbols.
- Use logo_library for logos, partner marks, customer marks, and social logos.
- Use CSS, Tailwind, and GSAP for hover animations, scroll reveals, parallax, glows, and transitions.
- Do not create video or lottie assets just because a section has animations.
- Create video only for a hero/product demo/background media section that explicitly needs video playback.
- Create lottie only for a specific reusable animated illustration or interface micro-animation.
- For scroll motion, parallax motion, card reveals, CTA hover, section transitions, and navigation motion, set animation_required true on the relevant visual asset when useful, but let the Code Agent implement the motion with GSAP.
- Generated assets must look premium, product-ready, clean, and high-end.

Return ONLY valid JSON matching AssetOutput.
Do not include markdown.
Do not wrap JSON in code fences.

The top-level object must contain:
project_style, design_theme, assets.

Each asset must contain exactly:
asset_id, page_name, section_name, purpose, asset_type, priority, source_strategy, generation_required, prompt, negative_prompt, style_keywords, animation_required, animation_description, width, height, format, output_filename, source_output_filename.

Allowed asset_type values:
image, video, icon, logo, lottie, illustration, svg_diagram, background.

Allowed priority values:
low, medium, high, critical.

Allowed source_strategy values:
generate, internet, icon_library, logo_library, client_provided.

Use "lottie", not "lottie_animation".
Use "generate", not "generated".

Do not generate common UI icons or company/client logos.
Use source_strategy "icon_library" for UI icons.
Use source_strategy "logo_library" for brand, company, client, partner, or social logos.
Set generation_required false for icon_library and logo_library assets.
Set prompt null for icon_library and logo_library assets.
Only use source_strategy "generate" for custom visuals that cannot come from a library.

width and height must be integers, not strings like "1920x1080".
format must be a simple string like "png", "jpg", "svg", "json", or "mp4".

style_keywords must always be an array of strings.
Use [] when there are no style keywords.
Never use null for style_keywords.

Only these fields may be null:
prompt, negative_prompt, animation_description, source_output_filename.

If generation_required is true, prompt must be a non-empty string.
If generation_required is false, prompt may be null.


for Example:
{
  "project_style": "Premium modern AI SaaS",
  "design_theme": "Dark futuristic interface with restrained gradients",
  "assets": [
    {
      "asset_id": "homepage_hero_visual",
      "page_name": "Homepage",
      "section_name": "Hero",
      "purpose": "Support the hero value proposition with an AI platform visual.",
      "asset_type": "image",
      "priority": "critical",
      "source_strategy": "generate",
      "generation_required": true,
      "prompt": "Premium futuristic AI dashboard hero visual, dark interface, glowing data nodes, clean SaaS composition.",
      "negative_prompt": "blurry, low quality, cluttered, unreadable text",
      "style_keywords": ["premium", "futuristic", "AI", "SaaS"],
      "animation_required": false,
      "animation_description": null,
      "width": 1600,
      "height": 900,
      "format": "png",
      "output_filename": "homepage_hero_visual.png",
      "source_output_filename": null
    }
  ]
}
"""



class AssetAgent:

  def __init__(self):
    
    self.model = deepseek_llm()


  def _normalize_asset_payload(
      self,
      payload: dict
  ) -> dict:

      for asset in payload.get("assets", []):
          if not isinstance(asset, dict):
              continue

          if asset.get("style_keywords") is None:
              asset["style_keywords"] = []

          if asset.get("asset_type") == "lottie_animation":
              asset["asset_type"] = "lottie"

          if asset.get("source_strategy") == "generated":
              asset["source_strategy"] = "generate"

          if not asset.get("source_strategy"):
              asset["source_strategy"] = "client_provided"

          if asset.get("source_strategy") in {
              "icon_library",
              "logo_library",
              "internet",
              "client_provided",
          }:
              asset["generation_required"] = False

          if asset.get("source_strategy") == "generate":
              asset["generation_required"] = bool(
                  asset.get("prompt")
              )

          if "generation_required" not in asset:
              asset["generation_required"] = False

          if (
              asset.get("generation_required") is True
              and not asset.get("prompt")
          ):
              asset["generation_required"] = False
              asset["source_strategy"] = "client_provided"

          if asset.get("generation_required") is False:
              if asset.get("prompt") in ("", None):
                  asset["prompt"] = None

          if not asset.get("negative_prompt"):
              asset["negative_prompt"] = None

          if not asset.get("animation_description"):
              asset["animation_description"] = None

          if not asset.get("source_output_filename"):
              asset["source_output_filename"] = None

          if "animation_required" not in asset:
              asset["animation_required"] = False

      return payload


  async def _parse_asset_output_with_retry(
      self,
      messages: list,
      page_name: str
  ) -> AssetOutput:

      max_attempts = int(
          os.getenv(
              "ASSET_JSON_ATTEMPTS",
              "4"
          )
      )
      previous_content = ""
      previous_error = ""

      for attempt in range(1, max_attempts + 1):
          current_messages = messages

          if previous_error:
              try:
                  previous_json = extract_json_object(
                      previous_content
                  )
              except Exception:
                  previous_json = previous_content[:4000]

              current_messages = [
                  messages[0],
                  HumanMessage(
                      content=(
                          messages[1].content
                          + f"""

Previous asset JSON was invalid.

Validation error:
{previous_error}

Previous invalid JSON:
{previous_json}

Repair instructions:
- Return the complete corrected AssetOutput JSON object.
- Every asset must include generation_required as true or false.
- Every asset must include all required fields.
- Do not return only the broken asset.
- Do not include explanation.
"""
                      )
                  )
              ]

          response = await resilient_ainvoke(
              self.model,
              current_messages,
              "asset_plan_output_json"
          )

          previous_content = response.content

          try:
              payload = load_model_json(
                  response.content
              )
              payload = self._normalize_asset_payload(
                  payload
              )

              return AssetOutput.model_validate(
                  payload
              )
          except Exception as error:
              previous_error = str(error)
              logger.warning(
                  "Asset JSON validation failed",
                  extra={
                      "page": page_name,
                      "attempt": attempt,
                      "max_attempts": max_attempts,
                      "error_type": type(error).__name__,
                      "error": previous_error
                  }
              )

              if attempt >= max_attempts:
                  raise

      raise RuntimeError(
          f"Failed to generate valid AssetOutput for {page_name}"
      )


  async def _plan_assets_for_page(
      self,
      page_output: PageDesignOutput
  ) -> AssetOutput:

      page_name = page_output.pages[0].page_name
      print(
          f"Asset prompt page: {page_name}"
      )

      user_prompt = f"""

              Page Design:

              {page_output.model_dump_json(indent=2)}

              Determine every asset required for this page only.
              Avoid duplicate assets.

              Reuse assets whenever possible.

              Only create assets that are actually required by the page design.
              Keep this page asset plan small and implementation-friendly.

              Asset count limits:
              - Maximum 6 generated assets for this page.
              - Prefer 3 to 5 generated assets.
              - Do not generate assets for every card, badge, icon, button, or small decorative element.
              - Use icon_library for normal UI icons.
              - Use logo_library for logos and customer/partner marks.

              Animation and motion rules:
              - Scroll reveals, parallax, hover glows, section transitions, navigation motion, and CTA feedback must be implemented later with GSAP/CSS.
              - Do not create video or lottie assets just because animations are listed.
              - Create asset_type "video" only if the page design explicitly needs video playback or cinematic product media.
              - Create asset_type "lottie" only if the page design explicitly needs reusable animated UI media.
              - When an image/background should participate in parallax or scroll motion, set animation_required true and describe the GSAP motion in animation_description.

              Do not generate decorative assets without purpose.
              Every generated asset must be premium, high-end, polished, and visible in the final UI.

              For each asset decide:

              - type
              - purpose
              - source strategy
              - generation prompt
              - dimensions
              - format

              Return AssetOutput.


            """

      messages = [
         
         SystemMessage(
            
            content=SYSTEM_PROMPT
            
         ),

         HumanMessage(
            content=user_prompt
         )

      ]


      return await self._parse_asset_output_with_retry(
          messages,
          page_name
      )
        


  async def plan_assets(
      self,
      page_output:PageDesignOutput
  ) -> AssetOutput:

      page_asset_outputs: list[AssetOutput] = []

      for page in page_output.pages:
          single_page_output = PageDesignOutput(
              global_rules=page_output.global_rules,
              pages=[
                  page
              ]
          )
          page_asset_outputs.append(
              await self._plan_assets_for_page(
                  single_page_output
              )
          )

      merged_assets: list[AssetRequirement] = []
      seen_asset_ids: set[str] = set()

      for output in page_asset_outputs:
          for asset in output.assets:
              asset_id = asset.asset_id
              if asset_id in seen_asset_ids:
                  asset_id = (
                      f"{asset.page_name.lower().replace(' ', '_')}_"
                      f"{asset.section_name.lower().replace(' ', '_')}_"
                      f"{asset.asset_id}"
                  )
                  asset = asset.model_copy(
                      update={
                          "asset_id": asset_id
                      }
                  )

              seen_asset_ids.add(
                  asset_id
              )
              merged_assets.append(
                  asset
              )

      result = AssetOutput(
          project_style=(
              page_asset_outputs[0].project_style
              if page_asset_outputs
              else "Generated website"
          ),
          design_theme=(
              page_asset_outputs[0].design_theme
              if page_asset_outputs
              else "Generated visual system"
          ),
          assets=merged_assets
      )

      generated_by_page: dict[str, int] = {}
      capped_assets: list[AssetRequirement] = []

      for asset in result.assets:
          page_key = asset.page_name.lower()
          is_generated = (
              asset.source_strategy == SourceStrategy.GENERATE
              and asset.generation_required
          )

          if is_generated:
              generated_count = generated_by_page.get(
                  page_key,
                  0
              )
              if generated_count >= 6:
                  continue
              generated_by_page[page_key] = generated_count + 1

          capped_assets.append(
              asset
          )

      result = result.model_copy(
          update={
              "assets": capped_assets
          }
      )

      if not result.assets:
          raise ValueError(
              "No assets generated."
          )

      for asset in result.assets:

          if not asset.asset_type:
              raise ValueError(
                  f"{asset.asset_id} missing type."
              )

          if (
              asset.generation_required
              and not asset.prompt
          ):
              raise ValueError(
                  f"{asset.asset_id} missing prompt."
              )
          
          if not asset.source_strategy:
              raise ValueError(
                  f"{asset.asset_id} missing source strategy."
              )
          

      with open(
          "asset_output.json",
          "w",
          encoding="utf-8"
      ) as f:

          f.write(
              result.model_dump_json(
                  indent=2
              )
          )

      return result




# if __name__ == "__main__":
    
#     import asyncio
#     import json

#     async def main():

#         print("loading arch")
#         with open(
#             "page_design_output.json",
#             "r",
#             encoding="utf-8"
#         ) as f:
#             page = (
#                 PageDesignOutput
#                 .model_validate_json(
#                     f.read()
#                 )
#             )


#         agent = AssetAgent()

#         result = await agent.plan_assets(
#             page,
#         )

#         print(
#             result.model_dump_json(
#                 indent=2
#             )
#         )

#     asyncio.run(main())
