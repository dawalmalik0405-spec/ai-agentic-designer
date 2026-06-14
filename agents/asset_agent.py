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

Return only valid AssetOutput.
"""



class AssetAgent:

  def __init__(self):
    
    self.model = (
        reason_llm()
        .with_structured_output(
          AssetOutput
        )
    )


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


      result = await self.model.ainvoke(
          messages
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