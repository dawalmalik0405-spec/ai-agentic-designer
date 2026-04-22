import json
import re
from ai_agentic_designer.agents.llm import llm


SYSTEM_PROMPT = """
You are an elite website UI agent.

Your task is to convert structured page blueprints and design systems
into premium renderable UI blueprints.

You intelligently decide:
- component variants
- visual hierarchy
- responsive composition
- section layouts
- alignment
- spacing usage
- card/grid styles
- motion intent

Rules:
- Return valid JSON only
- No markdown
- No explanations
- Use all pages provided
- Use all sections provided
- Do not invent random pages
- Keep layouts premium and modern
"""


def generate_ui(prompt, pages, design):

    ui_prompt = f"""
User Request:
{prompt}

Page Agent Output:
{json.dumps(pages, indent=2)}

Design Agent Output:
{json.dumps(design, indent=2)}

Return ONLY valid JSON in this format:

{{
  "pages": [
    {{
      "name": "home",
      "route": "/",
      "ui_sections": [
        {{
          "type": "navbar",
          "variant": "sticky_glass",
          "layout": "horizontal",
          "motion": "fade_down"
        }},
        {{
          "type": "hero",
          "variant": "split_left_copy_right_mockup",
          "layout": "2_column",
          "motion": "stagger_reveal"
        }}
      ]
    }}
  ]
}}

Rules:
- Use ALL pages from Page Agent output
- Use ALL sections from each page
- Do not remove sections
- Do not add random pages
- Choose premium section variants
- Use design palette / typography / style family
- Navbar/Footer = polished public style
- Dashboard pages = sidebar/topbar layouts
- Hero sections = strong conversion layouts
- Pricing = clean comparison cards
- Features = card grid or bento grid
- Return JSON only
"""

    response = llm(ui_prompt, SYSTEM_PROMPT=SYSTEM_PROMPT)
    print("RAW UI RESPONSE:", response)

    try:
        match = re.search(r'\{[\s\S]*\}', response)

        if not match:
            raise ValueError("No JSON found")

        ui = json.loads(match.group())

    except:
        ui = {
            "pages": [
                {
                    "name": "home",
                    "route": "/",
                    "ui_sections": [
                        {
                            "type": "navbar",
                            "variant": "default_navbar",
                            "layout": "horizontal",
                            "motion": "fade_down"
                        },
                        {
                            "type": "hero",
                            "variant": "default_hero",
                            "layout": "2_column",
                            "motion": "fade_up"
                        },
                        {
                            "type": "footer",
                            "variant": "default_footer",
                            "layout": "stacked",
                            "motion": "fade_in"
                        }
                    ]
                }
            ]
        }

    return ui


# TEST DATA

# prompt = "Create futuristic AI SaaS platform with premium dashboard feel"

# pages = {
#     "pages": [
#         {
#             "name": "home",
#             "route": "/",
#             "sections": [
#                 "navbar",
#                 "hero",
#                 "features",
#                 "pricing",
#                 "footer"
#             ]
#         },
#         {
#             "name": "dashboard",
#             "route": "/dashboard",
#             "sections": [
#                 "sidebar",
#                 "topbar",
#                 "stats_cards",
#                 "charts"
#             ]
#         }
#     ]
# }

# design = {
#     "style_family": "premium futuristic",
#     "mode": "dark",
#     "palette": {
#         "primary": "#00F5D4",
#         "secondary": "#7C3AED",
#         "accent": "#22D3EE",
#         "background": "#0F0F1A",
#         "surface": "#1E1E2F",
#         "text": "#FFFFFF"
#     },
#     "typography": {
#         "heading": "Space Grotesk",
#         "body": "Inter"
#     },
#     "motion": "smooth_premium",
#     "surface_style": "glassmorphism"
# }

# ui = generate_ui(prompt, pages, design)

# print(json.dumps(ui, indent=2))