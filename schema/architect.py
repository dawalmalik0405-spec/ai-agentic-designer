from pydantic import BaseModel
from typing import List


# =====================================================
# PROJECT SUMMARY
# =====================================================

class ProjectSummary(BaseModel):
    project_type: str
    business_goal: str
    primary_conversion_goal: str
    target_audience: List[str]
    unique_value_proposition: str


# =====================================================
# USER EXPERIENCE
# =====================================================







# =====================================================
# DESIGN DIRECTION
# =====================================================



class DesignDirection(BaseModel):
    style: str
    mood: str
    visual_hierarchy: list[str]
    inspiration_keywords: list[str]


# =====================================================
# MOTION DIRECTION
# =====================================================

class MotionDirection(BaseModel):

    hero_animation: str

    scroll_animation: str

    page_transition: str

    hover_effects: list[str]

    micro_interactions: list[str]

    storytelling_style: str

    immersive_experience: bool


# =====================================================
# PAGE BLUEPRINTS
# =====================================================

class SectionBlueprint(BaseModel):

    name: str

    purpose: str

    priority: int


class PageBlueprint(BaseModel):
    name: str

    route: str

    goal: str

    sections: List[SectionBlueprint]


# =====================================================
# RESEARCH REQUIREMENTS
# =====================================================

class ResearchRequirements(BaseModel):

    industries: List[str]

    competitor_types: List[str]

    research_goals: List[str]

    inspiration_sources: List[str]

    search_queries: List[str]


# FINAL ARCHITECT OUTPUT
# =====================================================

class ArchitectOutput(BaseModel):

    project_summary: ProjectSummary

    design_direction: DesignDirection

    motion_direction: MotionDirection

    page_blueprints: List[PageBlueprint]

    missing_requirements: List[str]

    research_requirements: ResearchRequirements
