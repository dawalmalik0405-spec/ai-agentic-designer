from ai_agentic_designer.agents.llm import llm
from ai_agentic_designer.agents.site_spec import build_initial_site_spec, extract_json_object


SYSTEM_PROMPT = """
You are the planning agent for an autonomous website design system.

Return only valid JSON with this shape:
{
  "site_name": "string",
  "site_type": "marketing-site",
  "style_keywords": ["modern", "premium"],
  "pages": [
    {"name": "home", "goal": "Introduce the brand and drive conversions."},
    {"name": "about", "goal": "Explain the story and credibility."},
    {"name": "features", "goal": "Showcase product capabilities."},
    {"name": "pricing", "goal": "Present pricing and value."},
    {"name": "contact", "goal": "Give visitors a clear path to reach out."}
  ]
}

Rules:
- Always plan for the multi-page marketing core.
- Keep page names limited to home, about, features, pricing, contact.
- Use concise style keywords.
- Do not return explanations.
"""


def planner(prompt: str) -> dict:
    planning_prompt = f"""
User Request:
{prompt}

Create the structured website planning metadata for a multi-page marketing site.
Return JSON only.
"""

    response = llm(planning_prompt, system_prompt=SYSTEM_PROMPT)
    planner_output = extract_json_object(response)
    return build_initial_site_spec(prompt, planner_output)
