from langchain_core.messages import HumanMessage, SystemMessage

from schema.architect import ArchitectOutput

from agents.llm import deepseek_llm
import asyncio


SYSTEM_PROMPT = """
You are an elite Website Architect.

Your responsibility is to create a high-level
website architecture.

Your job is NOT to design the website.

Do NOT generate:

- exact layouts
- exact animations
- exact interactions
- exact component behavior
- exact content
- exact copywriting
- exact visual effects
- exact implementation details

Your job is ONLY to determine:

- project summary
- target audience
- business goals
- design direction
- motion direction
- required pages
- required sections
- research requirements
- missing requirements

The architecture must help downstream agents:

1. Research Agent
2. Visual Asset Agent
3. Design System Agent
4. Page Design Agent
5. Code Agent

Think strategically.

Stay at the architecture level.

Return only valid structured output.
"""



STYLE_GUIDANCE = {
    "glassmorphism":
        "frosted glass, blur, transparency, layered depth",

    "neo_brutalism":
        "hard borders, bold typography, flat colors",

    "minimalism":
        "clean layouts, whitespace, restrained visuals",

    "liquid_glass":
        "visionOS style, liquid blur, luminous surfaces",

    "claymorphism":
        "soft surfaces, rounded shapes, playful depth",

    "skeuomorphism":
        "realistic textures, physical metaphors"
}







class ArchitectAgent:

    def __init__(self):

        print("Initializing model...")

        self.model = (
            deepseek_llm()
            .with_structured_output(
                ArchitectOutput
            )
        )

        print("Model initialized.")

    


    async def build_architecture(
        self,
        prompt: str,
        selected_style: str,
    ) -> ArchitectOutput:
        

        print("Building prompt...")
        
        style_guidance = STYLE_GUIDANCE.get(
            selected_style.lower(),
            "premium modern web design"
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),

            HumanMessage(
                content=f"""
User Request:   

{prompt}

Selected Style:

{selected_style}


Style Guidance:
{style_guidance}


Target Technical Stack:

Frontend:
- React
- TailwindCSS

Animation:
- Framer Motion
- GSAP




Create a complete website architecture.

Stay at a strategic level.

Do not provide implementation details.

Do not describe exact animations.

Do not describe exact interactions.

Do not describe exact component behavior.

Do not describe exact content.

Only define goals, structure, priorities,
and research direction.


Research Sources To Consider:

- Apple
- Stripe
- Linear
- Vercel
- OpenAI
- Anthropic
- Airbnb
- Framer
- Magic UI
- Uiverse
- Mobbin
- Dribbble
- Awwwards
- Landbook
- One Page Love
- SaaSFrame
- v0 by Vercel

When creating research requirements,
generate search queries that help discover:

- modern AI startup websites
- premium SaaS websites
- hero section inspiration
- typography inspiration
- motion design inspiration
- interaction patterns
- component libraries
- premium landing pages
- glassmorphism examples
- AI product websites

Infer all missing requirements.

Return a detailed ArchitectOutput.
"""
            )
        ]


        print("Calling LLM...")

        result = await self.model.ainvoke(messages)

        print("LLM returned result.")

        if not result.page_blueprints:
            raise ValueError(
                "Architect produced no pages."
            )

        if not result.research_requirements.search_queries:
            raise ValueError(
                "Architect produced no search queries."
            )

        if not result.missing_requirements:
            raise ValueError(
                "Architect failed to infer missing requirements."
            )

        return result





# if __name__ == "__main__":

#     import time

#     print("Creating Architect Agent...")

#     agent = ArchitectAgent()

#     print("Running Architecture Generation...")

#     start = time.time()

#     result = asyncio.run(
#         agent.build_architecture(
#             prompt="""
#             Build a premium AI startup website
#             for autonomous AI agents.
#             """,
#             selected_style="glassmorphism"
#         )
#     )

#     print(
#         f"Architect time: "
#         f"{time.time() - start:.2f}s"
#     )

#     print(
#         result.model_dump_json(
#             indent=2
#         )
#     )

#     with open(
#         "architect_output.json",
#         "w",
#         encoding="utf-8"
#     ) as f:
#         f.write(
#             result.model_dump_json(
#                 indent=2
#             )
#         )