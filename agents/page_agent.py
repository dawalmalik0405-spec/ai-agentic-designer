from schema.desighn import DesignSystemOutput
from schema.architect import ArchitectOutput
from schema.page_d import PageDesignOutput, PageDesign, GlobalDesignRules

from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)
from agents.llm import deepseek_llm
from agents.json_utils import extract_json_object, parse_model_json
from agents.resilient_llm import resilient_ainvoke
import logging
import os

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
Preserve the page identity from the Page Blueprint.
Do not rename the page to Homepage unless the blueprint page name is Homepage.
Generate enough sections to satisfy the Page Blueprint.
Homepage pages should usually have 5 to 7 sections.
Supporting pages should usually have 3 to 5 sections.
Each section must have at most 4 components.
animations must have 1 to 3 concrete motion strings.
interactions must have 1 to 3 concrete interaction strings.
content_priority must have at most 4 strings.
Keep every string under 120 characters.
Your entire response must be parseable by JSON.parse.
End the response immediately after the final closing brace.
Use English only.
Use premium visual direction from the Design System.
Prefer layered depth, stronger typography, polished spacing, glass or elevated surfaces when appropriate.
Avoid generic plain SaaS sections unless the design system explicitly requires minimalism.

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
    self.model = deepseek_llm()


  async def _generate_single_page(
      self,
      architect_output: ArchitectOutput,
      design_output: DesignSystemOutput,
      page_blueprint
  ) -> PageDesign:

      base_user_prompt = f"""
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

          Radius:
          {design_output.radius.model_dump_json(indent=2)}

          Shadows:
          {design_output.shadows.model_dump_json(indent=2)}

          Grid:
          {design_output.grid.model_dump_json(indent=2)}

          Motion:
          {design_output.motion.model_dump_json(indent=2)}

          Design Principles:
          {[p.model_dump_json(indent=2) for p in design_output.design_principles]}

          Component Guidelines:
          {[c.model_dump_json(indent=2) for c in design_output.component_guidelines]}

          Create only this one PageDesign JSON object.
          """

      max_attempts = int(
          os.getenv(
              "PAGE_JSON_ATTEMPTS",
              "4"
          )
      )
      previous_content = ""
      previous_error = ""

      for attempt in range(1, max_attempts + 1):
          repair_context = ""

          if previous_error:
              try:
                  previous_json = extract_json_object(
                      previous_content
                  )
              except Exception:
                  previous_json = previous_content[:4000]

              repair_context = f"""

          Previous response was invalid.

          Validation error:
          {previous_error}

          Previous invalid JSON:
          {previous_json}

          Repair instructions:
          - Return the complete corrected PageDesign JSON object.
          - Every section must include section_goal.
          - Do not omit any required field.
          - Do not return only the missing field.
          - Do not include explanation.
          """

          messages = [

              SystemMessage(
                  content=SYSTEM_PROMPT
              ),

              HumanMessage(
                  content=base_user_prompt + repair_context
              )
          ]

          prompt = messages[1].content

          print(
              f"Page prompt size for {page_blueprint.name}: {len(prompt)} characters"
          )

          response = await resilient_ainvoke(
              self.model,
              messages,
              "page_design_output_json"
          )

          previous_content = response.content

          try:
              return parse_model_json(
                  PageDesign,
                  response.content
              )
          except Exception as error:
              previous_error = str(error)
              logger.warning(
                  "Page JSON validation failed",
                  extra={
                      "page": page_blueprint.name,
                      "attempt": attempt,
                      "max_attempts": max_attempts,
                      "error_type": type(error).__name__,
                      "error": previous_error
                  }
              )

              if attempt >= max_attempts:
                  raise

      raise RuntimeError(
          f"Failed to generate valid PageDesign for {page_blueprint.name}"
      )

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

      page = await self._generate_single_page(
          architect_output,
          design_output,
          page_blueprint
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

    logger.info(
        "Generated %s pages",
        len(result.pages)
    )

    return result


  async def design_single_page(
      self,
      architect_output: ArchitectOutput,
      design_output: DesignSystemOutput
  ) -> PageDesignOutput:
    """Generate only the first page blueprint for prompt-by-prompt workflows."""

    logger.info(
        "Starting single page design generation"
    )

    if not architect_output.page_blueprints:
        raise ValueError(
            "No page blueprint available."
        )

    page = await self._generate_single_page(
        architect_output,
        design_output,
        architect_output.page_blueprints[0]
    )

    result = PageDesignOutput(
        global_rules=GlobalDesignRules(
            navigation_style="Sticky top navigation with concise links and one primary CTA.",
            footer_style="Structured footer with product, company, resource, and legal links.",
            transition_style="Subtle fade and slide transitions between pages."
        ),
        pages=[page]
    )

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

    logger.info(
        "Generated single page: %s",
        page.page_name
    )

    return result




# if __name__ == "__main__":

#   import asyncio

#   def sample_architecture() -> ArchitectOutput:
#     return ArchitectOutput.model_validate(
#         {
#             "project_summary": {
#                 "project_type": "AI SaaS website",
#                 "business_goal": "Convert visitors into product signups.",
#                 "primary_conversion_goal": "Start a free trial.",
#                 "target_audience": [
#                     "startup founders",
#                     "product teams",
#                 ],
#                 "unique_value_proposition": (
#                     "An AI workspace that automates execution work and gives teams sharper insight."
#                 ),
#             },
#             "design_direction": {
#                 "style": "premium glassmorphism",
#                 "mood": "polished, modern, confident",
#                 "visual_hierarchy": [
#                     "Hero",
#                     "Features",
#                     "Pricing",
#                     "CTA",
#                 ],
#                 "inspiration_keywords": [
#                     "Linear",
#                     "Stripe",
#                     "OpenAI",
#                 ],
#             },
#             "motion_direction": {
#                 "hero_animation": "Cinematic hero reveal with layered product visual.",
#                 "scroll_animation": "Staggered section reveals on scroll.",
#                 "page_transition": "Subtle fade and slide between pages.",
#                 "hover_effects": [
#                     "card lift",
#                     "CTA glow",
#                 ],
#                 "micro_interactions": [
#                     "button hover feedback",
#                     "navigation underline",
#                 ],
#                 "storytelling_style": "Progressive product narrative.",
#                 "immersive_experience": True,
#             },
#             "page_blueprints": [
#                 {
#                     "name": "Homepage",
#                     "route": "/",
#                     "goal": "Introduce the product and drive signup.",
#                     "sections": [
#                         {
#                             "name": "Hero",
#                             "purpose": "Communicate the core value proposition.",
#                             "priority": 1,
#                         },
#                         {
#                             "name": "Features",
#                             "purpose": "Show core product capabilities.",
#                             "priority": 2,
#                         },
#                         {
#                             "name": "Social Proof",
#                             "purpose": "Build trust with customer evidence.",
#                             "priority": 2,
#                         },
#                     ],
#                 },
#                 {
#                     "name": "Pricing Page",
#                     "route": "/pricing",
#                     "goal": "Explain plans and convert qualified buyers.",
#                     "sections": [
#                         {
#                             "name": "Pricing Hero",
#                             "purpose": "Frame pricing around product value.",
#                             "priority": 1,
#                         },
#                         {
#                             "name": "Plans",
#                             "purpose": "Compare pricing tiers clearly.",
#                             "priority": 1,
#                         },
#                     ],
#                 },
#             ],
#             "missing_requirements": [],
#             "research_requirements": {
#                 "industries": [
#                     "SaaS",
#                     "AI productivity",
#                 ],
#                 "competitor_types": [
#                     "AI productivity tools",
#                 ],
#                 "research_goals": [
#                     "premium SaaS page structure",
#                 ],
#                 "inspiration_sources": [
#                     "Linear",
#                     "Stripe",
#                 ],
#                 "search_queries": [
#                     "premium AI SaaS website design",
#                 ],
#             },
#         }
#     )

#   def sample_design_system() -> DesignSystemOutput:
#     return DesignSystemOutput.model_validate(
#         {
#             "colors": {
#                 "primary": "#7C3AED",
#                 "secondary": "#06B6D4",
#                 "accent": "#F59E0B",
#                 "background": "#070A12",
#                 "surface": "rgba(255,255,255,0.08)",
#                 "success": "#22C55E",
#                 "warning": "#F59E0B",
#                 "error": "#EF4444",
#                 "dark_background": "#030712",
#                 "dark_surface": "#101827",
#             },
#             "typography": {
#                 "heading_font": "Inter",
#                 "body_font": "Inter",
#                 "weights": [
#                     "400",
#                     "500",
#                     "600",
#                     "700",
#                 ],
#                 "scale": {
#                     "h1": "64px",
#                     "h2": "44px",
#                     "h3": "30px",
#                     "h4": "22px",
#                     "body_large": "18px",
#                     "body_medium": "16px",
#                     "body_small": "14px",
#                     "caption": "12px",
#                 },
#             },
#             "spacing": {
#                 "xxs": "4px",
#                 "xs": "8px",
#                 "sm": "12px",
#                 "md": "16px",
#                 "lg": "24px",
#                 "xl": "40px",
#                 "xxl": "80px",
#             },
#             "borders": {
#                 "thin": "1px",
#                 "normal": "2px",
#                 "thick": "4px",
#             },
#             "radius": {
#                 "small": "6px",
#                 "medium": "10px",
#                 "large": "16px",
#                 "pill": "999px",
#             },
#             "shadows": {
#                 "small": "0 4px 12px rgba(0,0,0,0.16)",
#                 "medium": "0 16px 48px rgba(0,0,0,0.24)",
#                 "large": "0 30px 90px rgba(0,0,0,0.35)",
#             },
#             "breakpoints": {
#                 "mobile": "480px",
#                 "tablet": "768px",
#                 "laptop": "1024px",
#                 "desktop": "1280px",
#                 "wide": "1536px",
#             },
#             "grid": {
#                 "columns": 12,
#                 "gutter": "24px",
#                 "max_width": "1200px",
#                 "content_width": "760px",
#             },
#             "motion": {
#                 "page_transition": {
#                     "duration": "400ms",
#                     "easing": "ease-out",
#                     "description": "Soft fade and slide.",
#                 },
#                 "hover_animation": {
#                     "duration": "180ms",
#                     "easing": "ease-out",
#                     "description": "Lift and glow on hover.",
#                 },
#                 "reveal_animation": {
#                     "duration": "600ms",
#                     "easing": "power3.out",
#                     "description": "Staggered reveal for grouped content.",
#                 },
#                 "section_reveal": {
#                     "duration": "700ms",
#                     "easing": "power3.out",
#                     "description": "Scroll-based section reveal.",
#                 },
#                 "hero_animation": {
#                     "duration": "900ms",
#                     "easing": "power3.out",
#                     "description": "Cinematic hero reveal.",
#                 },
#                 "scroll_patterns": [
#                     {
#                         "name": "Stagger reveal",
#                         "description": "Cards reveal sequentially.",
#                         "implementation": "Use GSAP ScrollTrigger.",
#                     }
#                 ],
#                 "interaction_patterns": [
#                     {
#                         "name": "CTA glow",
#                         "description": "CTA gains soft glow on hover.",
#                         "implementation": "Use a short hover timeline.",
#                     }
#                 ],
#             },
#             "design_principles": [
#                 {
#                     "title": "Premium clarity",
#                     "description": "Use sharp hierarchy with layered visual depth.",
#                 }
#             ],
#             "component_guidelines": [
#                 {
#                     "component": "Card",
#                     "purpose": "Group related content.",
#                     "guidelines": [
#                         "Use glass surface styling.",
#                         "Add hover lift.",
#                     ],
#                 }
#             ],
#         }
#     )

#   async def main():
#     print("Starting standalone PageAgent test...")
#     print("PageAgent provider: API")
#     print("PLANNING_MODEL:", os.getenv("PLANNING_MODEL", "mistralai/mistral-small-4-119b-2603"))

#     agent = PageAgent()
#     result = await agent.design_pages(
#         sample_architecture(),
#         sample_design_system()
#     )

#     print(
#         result.model_dump_json(
#             indent=2
#         )
#     )

#   asyncio.run(main())
