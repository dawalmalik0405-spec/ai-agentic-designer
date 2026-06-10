"""
Designing agent rebuild stub.

This module is intentionally stripped down so the agent can be rebuilt cleanly.
"""

from typing import Any


class DesigningAgent:
    async def generate_for_page(self, page_blueprint: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("DesigningAgent is a rebuild stub")


def get_designing_agent() -> DesigningAgent:
    return DesigningAgent()
