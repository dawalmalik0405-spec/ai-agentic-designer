from pydantic import BaseModel
from typing import List


class ComponentPlacement(BaseModel):
    component: str
    variant: str
    purpose: str
    style: str







class SectionDesign(BaseModel):

    order: int

    section_name: str

    section_goal: str

    layout: str

    visual_style: str

    components: List[ComponentPlacement]

    animations: List[str]

    interactions: List[str]

    content_priority: List[str]


class PageDesign(BaseModel):

    page_name: str

    page_goal: str

    priority: str

    sections: List[SectionDesign]



class GlobalDesignRules(BaseModel):

    navigation_style: str

    footer_style: str

    transition_style: str



class PageDesignOutput(BaseModel):

    global_rules: GlobalDesignRules

    pages: List[PageDesign]