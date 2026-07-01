from schema.desighn import DesignSystemOutput
from schema.architect import ArchitectOutput
from schema.page_d import PageDesignOutput

from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)
from agents.llm import reason_llm
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an elite Page Design Architect.

Your job is to transform a design system into
complete website page blueprints.

You do NOT generate code.

You do NOT generate CSS.

You do NOT generate Tailwind classes.

You do NOT generate implementation details.

You design:

- page structures
- section hierarchies
- section ordering
- section goals
- layout strategies
- component placement
- interaction allocation
- animation allocation
- content priorities

Every page must have:

- a clear business goal
- a clear user journey
- a logical information hierarchy

Every section must:

- support the page goal
- support the user journey

Use the design system strictly.

Return only valid PageDesignOutput.
"""






class PageAgent:

  def __init__(self):
    self.model = (
                reason_llm()
                .with_structured_output(
                    PageDesignOutput
                )
            )
    


  async def design_pages(
      self,
      architect_output: ArchitectOutput,
      design_output: DesignSystemOutput
  ) -> PageDesignOutput:
    

    logger.info(
        "Starting page design generation"
    )

    messages = [

        SystemMessage(
            content=SYSTEM_PROMPT
        ),

        HumanMessage(
            content=f"""
        Website Architecture

        Project:
        {architect_output.project_summary}

        Pages:
        {architect_output.page_blueprints}

        Motion Direction:
        {architect_output.motion_direction}

        Design System

        Colors:
        {design_output.colors}

        Typography:
        {design_output.typography}

        Spacing:
        {design_output.spacing}

        Motion:
        {design_output.motion}

        Component Guidelines:
        {design_output.component_guidelines}

        Design complete page blueprints.
        """
        )
    ]


    prompt = messages[1].content

    print(f"Prompt size: {len(prompt)} characters")

    result = await self.model.ainvoke(
        messages
    )

    if not result.pages:
        raise ValueError(
            "No pages generated."
        )

    for page in result.pages:

      if not page.page_goal:
          raise ValueError(
              f"{page.page_name} missing page goal."
          )

      if not page.sections:
          raise ValueError(
              f"{page.page_name} has no sections."
          )
        
      for section in page.sections:

        if not section.section_goal:
            raise ValueError(
                f"{section.section_name} missing goal."
            )

        if not section.components:
          logger.warning(
              "%s has no components",
              section.section_name
          )

    with open(
      "page_design_output.json",
      "w",
      encoding="utf-8"
  ) as f:

      f.write(
          result.model_dump_json(
              indent=2
          )
      )


    logger.info(
          "Generated %s pages",
          len(result.pages)
      )

    return result




# if __name__ == "__main__":
   

#   import asyncio
#   import json

#   async def main():

#       print("loading arch")
#       with open(
#           "architect_output.json",
#           "r",
#           encoding="utf-8"
#       ) as f:
#           architect = (
#               ArchitectOutput
#               .model_validate_json(
#                   f.read()
#               )
#           )


#       print("loading design")
#       with open(
#           "design_output.json",
#           "r",
#           encoding="utf-8"
#       ) as f:
#           design = (
#               DesignSystemOutput
#               .model_validate_json(
#                   f.read()
#               )
#           )

#       agent = PageAgent()

#       result = await agent.design_pages(
#           architect,
#           design
#       )

#       print(
#           result.model_dump_json(
#               indent=2
#           )
#       )

#   asyncio.run(main())