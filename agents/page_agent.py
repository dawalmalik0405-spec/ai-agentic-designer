import json

from ai_agentic_designer.agents.llm import llm
from ai_agentic_designer.agents.site_spec import compose_site_pages, extract_json_object


SYSTEM_PROMPT = """
You are the page composition agent for a multi-page website design system.

Return only valid JSON with this shape:
{
  "pages": [
    {
      "name": "home",
      "sections": [
        {
          "section_type": "hero",
          "variant": "split-visual",
          "purpose": "Introduce the offer",
          "content_brief": {
            "headline": "string",
            "supporting_text": "string"
          }
        }
      ]
    }
  ]
}

Rules:
- Use only these section types: navbar, hero, logo_cloud, stats_strip, feature_grid, feature_split, testimonial_grid, pricing_tiers, faq, cta, footer.
- Never return HTML.
- Navbar and footer can appear in the page section order, but their content_brief should be empty.
- Hero must appear on home.
- Pricing tiers may appear only on home or pricing.
- Keep the site desktop-focused and marketing-oriented.
"""


def generate_pages(site_spec: dict) -> dict:
    page_prompt = f"""
Project:
{json.dumps(site_spec["project"], indent=2)}

Pages:
{json.dumps(site_spec["pages"], indent=2)}

Component library:
{json.dumps(site_spec["component_library"], indent=2)}

Compose structured sections for each page.
Return JSON only.
"""

    response = llm(page_prompt, system_prompt=SYSTEM_PROMPT)
    page_payload = extract_json_object(response)
    return compose_site_pages(site_spec, page_payload)
