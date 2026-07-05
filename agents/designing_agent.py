"""
Designing agent rebuild stub.

This module is intentionally stripped down so the agent can be rebuilt cleanly.
"""

from schema.architect import ArchitectOutput
from schema.research import ResearchOutput
from schema.desighn import DesignSystemOutput
from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)

import logging


from agents.llm import deepseek_llm

logger = logging.getLogger(__name__)




SYSTEM_PROMPT = """
You are an elite Design System Architect.

Your job is NOT to design pages.

Your job is to create a reusable design system.

You must create:

- color system
- typography system
- spacing system
- radius system
- motion system
- component guidelines
- design principles


Do NOT generate:

- CSS
- Tailwind classes
- React code
- HTML
- implementation snippets

Describe systems and design decisions only.

The Code Agent will handle implementation.



Use:

1. Website architecture
2. Research findings

All decisions must be justified by the research.

Return ONLY valid JSON.
Do not include explanation.
Do not include markdown.
Do not wrap JSON in code fences.
The JSON must exactly match the DesignSystemOutput schema.
Do not wrap the output in a "design_system" key.
The top-level JSON object must directly contain:
colors, typography, spacing, borders, radius, shadows, breakpoints, grid, motion, design_principles, component_guidelines.

Use exactly these field names. Do not add nested token groups. Do not rename fields.
Every field typed as string must be a string, not an object.
component_guidelines must be an array, not an object.
design_principles must use title and description, not name.

The colors object must include all of these exact keys:
primary, secondary, accent, background, surface, success, warning, error, dark_background, dark_surface.

Every item in motion.scroll_patterns must include:
name, description, implementation.

Every item in motion.interaction_patterns must include:
name, description, implementation.

The value of "colors" must be a JSON object, not a string.

Valid JSON example:

{
  "colors": {
    "primary": "#2563EB",
    "secondary": "#64748B",
    "accent": "#8B5CF6",
    "background": "#FFFFFF",
    "surface": "#F8FAFC",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "dark_background": "#020617",
    "dark_surface": "#0F172A"
  },
  "typography": {
    "heading_font": "Inter",
    "body_font": "Inter",
    "weights": ["400", "500", "600", "700"],
    "scale": {
      "h1": "64px",
      "h2": "48px",
      "h3": "32px",
      "h4": "24px",
      "body_large": "18px",
      "body_medium": "16px",
      "body_small": "14px",
      "caption": "12px"
    }
  },
  "spacing": {
    "xxs": "4px",
    "xs": "8px",
    "sm": "12px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "xxl": "48px"
  },
  "borders": {
    "thin": "1px",
    "normal": "2px",
    "thick": "4px"
  },
  "radius": {
    "small": "4px",
    "medium": "8px",
    "large": "16px",
    "pill": "999px"
  },
  "shadows": {
    "small": "0 1px 2px rgba(0,0,0,0.08)",
    "medium": "0 8px 24px rgba(0,0,0,0.12)",
    "large": "0 24px 60px rgba(0,0,0,0.18)"
  },
  "breakpoints": {
    "mobile": "375px",
    "tablet": "768px",
    "laptop": "1024px",
    "desktop": "1440px",
    "wide": "1920px"
  },
  "grid": {
    "columns": 12,
    "gutter": "24px",
    "max_width": "1200px",
    "content_width": "min(100% - 32px, 1200px)"
  },
  "motion": {
    "page_transition": {
      "duration": "240ms",
      "easing": "ease-out",
      "description": "Smooth page-level transition."
    },
    "hover_animation": {
      "duration": "160ms",
      "easing": "ease-out",
      "description": "Subtle hover feedback."
    },
    "reveal_animation": {
      "duration": "420ms",
      "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
      "description": "Soft reveal for content blocks."
    },
    "section_reveal": {
      "duration": "520ms",
      "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
      "description": "Staggered section reveal."
    },
    "hero_animation": {
      "duration": "700ms",
      "easing": "ease-out",
      "description": "Premium hero entrance motion."
    },
    "scroll_patterns": [
      {
        "name": "Section reveal",
        "description": "Reveal sections as they enter the viewport.",
        "implementation": "Use opacity and translate motion."
      }
    ],
    "interaction_patterns": [
      {
        "name": "CTA hover",
        "description": "Buttons respond with restrained motion.",
        "implementation": "Use scale, border, or shadow change."
      }
    ]
  },
  "design_principles": [
    {
      "title": "Clarity first",
      "description": "Make the product value immediately understandable."
    }
  ],
  "component_guidelines": [
    {
      "component": "Button",
      "purpose": "Trigger primary and secondary user actions.",
      "guidelines": ["Use one primary CTA per section.", "Keep labels short."]
    }
  ]
}

"""

class DesigningAgent:


    def __init__(self):
  
        self.model = deepseek_llm()
                



    async def design_system(
        self,
        architect_output: ArchitectOutput,
        research_output: ResearchOutput
    ) -> DesignSystemOutput:


            logger.info(
                "Starting design system generation"
            )

            messages = [

                SystemMessage(
                    content=SYSTEM_PROMPT
                ),

                HumanMessage(
                    content=f"""
                    Website Architecture:

                    {architect_output.model_dump_json(indent=2)}

                    Research Findings:

                    {research_output.model_dump_json(indent=2)}

                    Create a production-grade design system.

                    Generate:

                    - color tokens
                    - typography tokens
                    - spacing tokens
                    - border tokens
                    - radius tokens
                    - shadow tokens
                    - breakpoint system
                    - grid system
                    - motion system
                    - design principles
                    - component guidelines

                    Avoid implementation details.

                    Focus on reusable design decisions.
                    """
                        )
                    ]




            response = await self.model.ainvoke(messages)

            print(response.content)

            result = DesignSystemOutput.model_validate_json(
                response.content
            )

            

            if not result.colors:
                raise ValueError(
                    "No color system generated."
                )

            if not result.typography:
                raise ValueError(
                    "No typography system generated."
                )

            if not result.motion:
                raise ValueError(
                    "No motion system generated."
                )



            

            logger.info(
                "Design system generated successfully"
            )
            return result





# if __name__ == "__main__":



#     import asyncio



#     async def main():
     
#         print("Loading Architect Output...")

#         with open(
#             "architect_output.json",
#             "r",
#             encoding="utf-8"
#         ) as f:

#             architecture = (
#                 ArchitectOutput
#                 .model_validate_json(
#                     f.read()
#                 )
#             )

#         print("Architect Output Loaded")


#         print("Loading Reasearch Output...")

#         with open(
#             "research_output.json",
#             "r",
#             encoding="utf-8"
#         ) as i:

#             reasearh = (
#                 ResearchOutput
#                 .model_validate_json(
#                     i.read()
#                 )
#             )

#         print("rsearch Output Loaded")


#         agent  = DesigningAgent()

#         design = await agent.design_system(
#             architecture,
#             reasearh
#         )

#         print(
#             design.model_dump_json(indent=2)
#         )

#         with open(
#             "design_output.json",
#             "w",
#             encoding="utf-8"
#         ) as f:

#             f.write(
#                 design.model_dump_json(
#                     indent=2
#                 )
#             )

#     asyncio.run(main())




    
            
    

        