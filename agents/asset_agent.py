from schema.asset import AssetOutput
from schema.page_d import PageDesignOutput

from agents.llm import reason_llm

from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)


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

- images
- videos
- icons
- diagrams
- illustrations
- logos
- lottie animations
- background assets

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
    
    self.model = reason_llm()
        


  async def plan_assets(
      self,
      page_output:PageDesignOutput
  ) -> AssetOutput:
    
      messages = [
         
         SystemMessage(
            
            content=SYSTEM_PROMPT
            
         ),

         HumanMessage(
            content=f"""

              Page Design:

              {page_output.model_dump_json(indent=2)}

              Determine every asset required.
              Avoid duplicate assets.

              Reuse assets whenever possible.

              Only create assets that are actually
              required by the page design.

              Do not generate decorative assets
              without purpose.

              For each asset decide:

              - type
              - purpose
              - source strategy
              - generation prompt
              - dimensions
              - format

              Return AssetOutput.


            """
         )

      ]


      response = await self.model.ainvoke(messages)

      result = AssetOutput.model_validate_json(
            response.content
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
