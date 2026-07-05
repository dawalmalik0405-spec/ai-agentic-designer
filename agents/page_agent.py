from schema.desighn import DesignSystemOutput
from schema.architect import ArchitectOutput
from schema.page_d import PageDesignOutput, PageDesign, GlobalDesignRules

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

Return ONLY valid JSON.
Do not include markdown.
Do not wrap JSON in code fences.
The JSON must exactly match one PageDesign object.
Do not return PageDesignOutput.
Do not include global_rules.
Do not add extra wrapper keys like page_design, design, or page.

The top-level object must contain only:
page_name, page_goal, priority, sections.

Every section must contain:
order, section_name, section_goal, layout, visual_style, components, animations, interactions, content_priority.

Every component must contain:
component, variant, purpose, style.

Arrays must be arrays.
Strings must be strings.
Numbers must be numbers.
Design only the single page blueprint provided by the user message.

Valid JSON example:

{
  "page_name": "Homepage",
  "page_goal": "Introduce the product and guide visitors toward the primary conversion action.",
  "priority": "high",
  "sections": [
    {
      "order": 1,
      "section_name": "Hero",
      "section_goal": "Communicate the core value proposition immediately.",
      "layout": "Full-width hero with headline, supporting copy, CTA group, and product visual.",
      "visual_style": "Premium modern layout with strong contrast and restrained motion.",
      "components": [
        {
          "component": "Button",
          "variant": "primary",
          "purpose": "Drive the main conversion action.",
          "style": "High-contrast filled button with subtle hover animation."
        }
      ],
      "animations": [
        "Fade in headline and CTA group on page load."
      ],
      "interactions": [
        "Primary CTA opens the conversion flow."
      ],
      "content_priority": [
        "Headline",
        "Primary CTA",
        "Product visual",
        "Trust signal"
      ]
    }
  ]
}
"""




class PageAgent:

  def __init__(self):
    self.model = reason_llm()

    


  async def design_pages(
      self,
      architect_output: ArchitectOutput,
      design_output: DesignSystemOutput
  ) -> PageDesignOutput:
    

    logger.info(
        "Starting page design generation"
    )

    pages = []

    for page_blueprint in architect_output.page_blueprints:

      messages = [

          SystemMessage(
              content=SYSTEM_PROMPT
          ),

          HumanMessage(
              content=f"""
          Project:
          {architect_output.project_summary.model_dump_json(indent=2)}

          Page Blueprint:
          {page_blueprint.model_dump_json(indent=2)}

          Design System:

          Colors:
          {design_output.colors.model_dump_json(indent=2)}

          Typography:
          {design_output.typography.model_dump_json(indent=2)}

          Spacing:
          {design_output.spacing.model_dump_json(indent=2)}

          Create only this one PageDesign JSON object.
          """
          )
      ]


      prompt = messages[1].content

      print(
          f"Page prompt size for {page_blueprint.name}: {len(prompt)} characters"
      )

      response = await self.model.ainvoke(messages)

      print(response.content)

      page = PageDesign.model_validate_json(
          response.content
      )

      pages.append(page)

    result = PageDesignOutput(
        global_rules=GlobalDesignRules(
            navigation_style="Sticky top navigation with concise links and one primary CTA.",
            footer_style="Structured footer with product, company, resource, and legal links.",
            transition_style="Subtle fade and slide transitions between pages."
        ),
        pages=pages
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
