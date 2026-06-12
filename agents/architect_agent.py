from langchain_core.messages import HumanMessage, SystemMessage

from schema.architect import ArchitectOutput

from llm import deepseek_llm


SYSTEM_PROMPT = """
You are an elite Website Architect.

You are simultaneously:

- Product Strategist
- UX Architect
- Conversion Strategist
- Design Strategist
- Motion Designer
- Interaction Designer

Your responsibility is to transform a user request into a complete
website architecture.

Infer missing requirements automatically.

Always determine:

- business goals
- target audience
- conversion goals
- user journeys
- information architecture
- page blueprints
- design direction
- motion direction
- premium features
- interaction requirements
- research requirements

Plan a premium production-grade website.

The output must be detailed enough that:

1. A Research Agent can perform competitor research.
2. A Design Agent can create a design system.
3. A Page Design Agent can design every page.
4. A Code Agent can implement the website.

Return only structured output.
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

        self.model = (
            deepseek_llm()
            .with_structured_output(
                ArchitectOutput
            )
        )

    


    def build_architecture(
        self,
        prompt: str,
        selected_style: str,
    ) -> ArchitectOutput:
        
        style_guidance = STYLE_GUIDANCE.get(
            selected_style.lower(),
            selected_style
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



- React
- TailwindCSS
- Framer Motion

Plan animations and interactions that can
realistically be implemented using this stack.


Create a complete website architecture.

Infer all missing requirements.

Return a detailed ArchitectOutput.
"""
            )
        ]

        result = self.model.invoke(messages)

        return result
    

