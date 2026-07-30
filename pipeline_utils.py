"""Shared model-response helpers used by the graph pipeline."""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel

from mcp_tools.resilience import ProviderResilience


ModelT = TypeVar("ModelT", bound=BaseModel)
logger = logging.getLogger(__name__)


def extract_json_object(text: str) -> str:
    """Extract the first complete JSON object from an LLM response."""
    content = (text or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    start = content.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(content)):
        char = content[index]
        if escaped:
            escaped = False
            continue
        if char == "\\\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start:index + 1]
    raise ValueError("Model response contains an incomplete JSON object.")


def parse_model_json(model: type[ModelT], content: str) -> ModelT:
    return model.model_validate_json(extract_json_object(content))


def load_model_json(content: str) -> dict[str, Any]:
    return json.loads(extract_json_object(content))


async def resilient_ainvoke(model: Any, messages: Any, operation_name: str) -> Any:
    model_name = getattr(model, "model", getattr(model, "model_name", model.__class__.__name__))
    provider_name = f"llm_{str(model_name).replace('/', '_')}"
    resilience = ProviderResilience.from_env(provider_name, logger=logger)
    return await resilience.execute(operation_name, lambda: model.ainvoke(messages))
