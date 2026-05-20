from typing import TypedDict


class AgentState(TypedDict, total=False):
    prompt: str
    selected_style: str
    plan: dict
    design: dict
    pages: dict
    ui: dict
    inspiration_data: dict
    files: dict
    current_agent: str
    is_complete: bool
    errors: list[str]
