from research import ResearchOutput
from architect import ArchitectOutput
from typing import TypedDict

class WebsiteBuilderState(TypedDict):

    user_prompt: str

    selected_style: str

    architect_output: ArchitectOutput | None

    research_output: ResearchOutput | None

    design_system_output: dict | None

    page_design_output: dict | None

    generated_code: str | None