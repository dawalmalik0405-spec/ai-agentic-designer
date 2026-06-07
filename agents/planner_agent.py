import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

try:
    from .llm import deepseek_llm
except ImportError:
    from llm import deepseek_llm


logger = logging.getLogger(__name__)

VALID_STYLES = {
    "glassmorphism",
    "skeuomorphism",
    "claymorphism",
    "minimalism",
    "liquid_glass",
    "neo_brutalism",
}

STYLE_GUIDANCE = {
    "glassmorphism": "frosted glass panels, blur, translucent layering, subtle neon accents",
    "skeuomorphism": "tactile surfaces, realistic depth, physical control styling",
    "claymorphism": "soft rounded forms, pastel surfaces, playful depth",
    "minimalism": "clean typography, quiet spacing, restrained contrast",
    "liquid_glass": "visionOS-style translucent surfaces, liquid highlights, saturated blur",
    "neo_brutalism": "hard borders, flat high contrast blocks, bold typography",
}

SYSTEM_PROMPT = """
You are the website planning agent.

Turn the user request into a build-ready website plan.

Return JSON only with these keys:
- plan
- design
- pages
- ui

The plan should:
- break the request into practical implementation steps
- infer missing website UI requirements the user did not mention
- stay buildable and concrete

Infer requirements such as:
- responsive layout
- navigation
- footer
- accessibility
- loading states
- empty states
- error states
- semantic structure
- clear call-to-action
- mobile behavior
"""


def _normalize_style(selected_style: str) -> str:
    style = str(selected_style or "").strip().lower().replace(" ", "_").replace("-", "_")
    if style not in VALID_STYLES:
        raise ValueError(f"selected_style must be one of: {', '.join(sorted(VALID_STYLES))}")
    return style


def _extract_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item["text"]))
        return "\n".join(part for part in parts if part).strip()

    return str(content).strip()


def _extract_json(text: str) -> dict[str, Any]:
    fenced = re.search(r"```json\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
    if fenced:
        return json.loads(fenced.group(1))

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Planner did not return JSON")

    return json.loads(match.group(0))


def _infer_request_context(prompt: str) -> dict[str, Any]:
    lower = prompt.lower()

    if any(token in lower for token in ["calculator", "editor", "dashboard", "tool", "utility", "app", "game"]):
        request_type = "interactive_product"
    elif any(token in lower for token in ["portfolio", "landing", "marketing", "brand", "agency", "startup", "saas"]):
        request_type = "marketing_site"
    elif any(token in lower for token in ["docs", "documentation", "knowledge base", "help center"]):
        request_type = "content_hub"
    else:
        request_type = "mixed_web_experience"
 
    inferred_requirements = [
        "responsive layout",
        "navigation",
        "footer",
        "accessibility",
        "loading states",
        "empty states",
        "error states",
        "semantic structure",
        "clear call-to-action",
        "mobile behavior",
    ]

    if request_type == "interactive_product":
        inferred_requirements.extend(
            [
                "stateful interactions",
                "clear feedback for controls",
                "usable primary workspace",
                "keyboard shortcuts where helpful",
            ]
        )
    elif request_type == "marketing_site":
        inferred_requirements.extend(
            [
                "strong hero section",
                "social proof",
                "pricing or conversion path",
                "feature highlights",
            ]
        )
    elif request_type == "content_hub":
        inferred_requirements.extend(
            [
                "search or filtering if content volume is high",
                "clear information hierarchy",
                "content categories or navigation rails",
            ]
        )

    return {
        "request_type": request_type,
        "inferred_requirements": inferred_requirements,
    }


def planner(prompt: str, selected_style: str) -> dict[str, Any]:
    style = _normalize_style(selected_style)
    context = _infer_request_context(prompt)
    model = deepseek_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"""
User request:
{prompt}

Selected style:
{style}

Style direction:
{STYLE_GUIDANCE[style]}

Request context:
{json.dumps(context, indent=2)}

Return JSON only with keys:
- plan
- design
- pages
- ui

Do not add markdown or commentary.
Infer missing UI requirements if they are needed for a real website.
Adapt the page structure to the request type instead of using canned layouts.
""".strip()
        ),
    ]

    raw = model.invoke(messages)
    text = _extract_text(raw)
    spec = _extract_json(text)

    if not isinstance(spec, dict):
        raise ValueError("Planner returned a non-object JSON payload")

    return spec




# if __name__ == "__main__":

#     test_prompt = "I want a website for my new startup that offers eco-friendly packaging solutions. The site should highlight our products, share our mission, and include a contact form."
#     test_style = "glassmorphism"

#     result = planner(test_prompt, test_style)
#     print(json.dumps(result, indent=2))
