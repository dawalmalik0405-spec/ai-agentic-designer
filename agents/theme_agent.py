import json

from ai_agentic_designer.agents.llm import llm
from ai_agentic_designer.agents.site_spec import build_complete_design_system, extract_json_object


SYSTEM_PROMPT = """
You are the theme agent for a website design system.

Return only valid JSON with this shape:
{
  "colors": {
    "primary": "#2563EB",
    "secondary": "#0EA5E9",
    "accent": "#14B8A6",
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#475569",
    "border": "#CBD5E1"
  },
  "typography": {
    "font_families": {
      "display": "Space Grotesk",
      "body": "Inter"
    }
  }
}

Rules:
- Use token-oriented design choices.
- Keep the system desktop-first.
- Do not introduce section-level one-off colors.
- Return JSON only.
"""


def generate_theme(site_spec: dict) -> dict:
    theme_prompt = f"""
Project:
{json.dumps(site_spec["project"], indent=2)}

Pages:
{json.dumps(site_spec["pages"], indent=2)}

Create a complete token-based design system for this website.
Return JSON only.
"""

    response = llm(theme_prompt, system_prompt=SYSTEM_PROMPT)
    theme_output = extract_json_object(response)
    return build_complete_design_system(site_spec, theme_output)
