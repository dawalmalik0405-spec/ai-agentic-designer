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

Return only valid DesignSystemOutput.
"""

class DesigningAgent:


    def __init__(self):
  
        self.model = (
                deepseek_llm()
                .with_structured_output(
                    DesignSystemOutput
                )
            )



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


            result = await self.model.ainvoke(messages)

            print(result)

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




    
            
    

        