from typing import TypedDict, Annotated


class AgentState(TypedDict, total=False):
    prompt: str
    selected_style: str
    plan: dict
    design: dict
    pages: dict
    ui: dict
    images: dict
    files: dict
    review: dict
    current_agent: Annotated[str, frozenset(["research", "planner", "code", "design", "review"])]
    repair_count: int
    is_complete: bool
    errors: list[str]
    # New fields for enhanced workflow
    design_system: dict
    animation_spec: dict
    page_templates: list
    inspiration_data: dict
    playwright_results: dict
    mcp_manager: object
