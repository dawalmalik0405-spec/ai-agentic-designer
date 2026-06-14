from pydantic import BaseModel
from typing import List


class WebsiteReference(BaseModel):
    name: str
    url: str
    reason: str


class ResearchOutput(BaseModel):

    references: List[WebsiteReference]

    hero_patterns: List[str]

    layout_patterns: List[str]

    typography_patterns: List[str]

    animation_patterns: List[str]

    interaction_patterns: List[str]

    color_patterns: List[str]

    premium_features: List[str]

    research_summary: str

    recommended_libraries: List[str] = []

    raw_research: str | None = None

    visual_patterns: List[str] = []

    component_patterns: List[str] = []
