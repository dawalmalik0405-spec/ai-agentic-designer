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

          if not asset.prompt:
              raise ValueError(
                  f"{asset.asset_id} missing prompt."
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

