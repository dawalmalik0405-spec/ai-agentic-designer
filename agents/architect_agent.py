from langchain_core.messages import HumanMessage, SystemMessage

from schema.architect import ArchitectOutput

from agents.llm import deepseek_llm
from agents.resilient_llm import resilient_ainvoke
import asyncio
import json
from pydantic import ValidationError


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

And return ONLY valid JSON.

Do NOT return markdown.

Do NOT explain anything.

Do NOT wrap the JSON inside ```json.

The JSON MUST exactly match this schema.

{
  "project_summary": {
    "project_type": "",
    "business_goal": "",
    "primary_conversion_goal": "",
    "target_audience": [],
    "unique_value_proposition": ""
  },
  "design_direction": {
    "style": "",
    "mood": "",
    "visual_hierarchy": [],
    "inspiration_keywords": []
  },
  "motion_direction": {
    "hero_animation": "",
    "scroll_animation": "",
    "page_transition": "",
    "hover_effects": [],
    "micro_interactions": [],
    "storytelling_style": "",
    "immersive_experience": true
  },
  "page_blueprints": [
    {
      "name": "",
      "route": "",
      "goal": "",
      "sections": [
        {
          "name": "",
          "purpose": "",
          "priority": ""
        }
      ]
    }
  ],
  "research_requirements": {
    "industries": [],
    "competitor_types": [],
    "research_goals": [],
    "inspiration_sources": [],
    "search_queries": []
  },
  "missing_requirements": []
}

priority MUST be an integer.

Allowed values:
1 = Critical
2 = High
3 = Medium
4 = Low

Do NOT use words like
critical
high
medium
low


visual_hierarchy MUST be a JSON array of strings.

Example:

[
  "Hero first",
  "Features second",
  "Pricing third",
  "Footer last"
]

The architecture must help downstream agents:

1. Research Agent
2. Visual Asset Agent
3. Design System Agent
4. Page Design Agent
5. Code Agent

Think strategically.

Stay at the architecture level.

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

        self.model = deepseek_llm()
        

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

First analyze the user request and infer the actual website type, audience,
business model, user journey, conversion goal, and content needs.

Create page_blueprints based on that analysis, not from a fixed template.

Unless the user explicitly asks for a single-page website, one-page site,
or landing page only, create a multi-page architecture with 3 to 5 pages.

For a product, SaaS, portfolio, agency, startup, or business website,
include a Homepage plus only the supporting pages that are relevant to the
specific user request.

Examples:
- SaaS/product: Homepage, Features, Pricing, Customers/Case Studies, Contact.
- Portfolio: Homepage, Work/Projects, About, Services, Contact.
- Restaurant: Homepage, Menu, Reservations, Gallery, Contact.
- Event: Homepage, Schedule, Speakers/Guests, Tickets, Venue.
- E-commerce: Homepage, Collection/Product pages, About, Support/Contact.

Do not add Pricing, Blog, About, Contact, Features, Showcase, or Case Studies
unless they make sense for the user's prompt.

Do not collapse all website goals into Homepage unless the request clearly
requires a single-page landing experience.

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
- jitter.video
- Iconsax.io
- Anime.js
- ui verse
- lenis
- Spline
- barba js 
- vengence ui
- ui lora 

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

IMPORTANT

The output MUST exactly match the JSON schema above.

Every field is required.

Do not rename fields.

Do not add extra fields.

Do not omit fields.

Return only JSON.

Return a detailed ArchitectOutput.
"""
            )
        ]


        print("Calling LLM...")

        response = await resilient_ainvoke(
            self.model,
            messages,
            "architect_output_json"
        )

        print(response.content)

        try:
            result = ArchitectOutput.model_validate_json(
                response.content
            )
        
        except ValidationError as e:
            print(e)
            raise 

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
