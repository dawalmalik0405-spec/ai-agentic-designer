from pydantic import BaseModel


class ColorSystem(BaseModel):
    primary: str
    secondary: str
    accent: str

    background: str
    surface: str

    success: str
    warning: str
    error: str

    dark_background: str
    dark_surface: str


class TypographyScale(BaseModel):
    h1: str
    h2: str
    h3: str
    h4: str

    body_large: str
    body_medium: str
    body_small: str

    caption: str


class TypographySystem(BaseModel):
    heading_font: str
    body_font: str

    weights: list[str]

    scale: TypographyScale




class MotionPattern(BaseModel):
    name: str
    description: str
    implementation: str



class MotionRule(BaseModel):
    duration: str
    easing: str
    description: str




class MotionSystem(BaseModel):

    page_transition: MotionRule

    hover_animation: MotionRule

    reveal_animation: MotionRule

    section_reveal: MotionRule

    hero_animation: MotionRule

    scroll_patterns: list[MotionPattern]

    interaction_patterns: list[MotionPattern]



class SpacingSystem(BaseModel):
    xxs: str
    xs: str
    sm: str
    md: str
    lg: str
    xl: str
    xxl: str

class BorderSystem(BaseModel):
    thin: str
    normal: str
    thick: str


class RadiusSystem(BaseModel):
    small: str
    medium: str
    large: str
    pill: str


class ShadowSystem(BaseModel):
    small: str
    medium: str
    large: str


class DesignPrinciple(BaseModel):
    title: str
    description: str



class ComponentGuideline(BaseModel):
    component: str
    purpose: str
    guidelines: list[str]




class Breakpoints(BaseModel):
    mobile: str
    tablet: str
    laptop: str
    desktop: str
    wide: str


class GridSystem(BaseModel):
    columns: int
    gutter: str
    max_width: str
    content_width: str




class DesignSystemOutput(BaseModel):

    colors: ColorSystem

    typography: TypographySystem

    spacing: SpacingSystem

    borders: BorderSystem

    radius: RadiusSystem

    shadows: ShadowSystem

    breakpoints: Breakpoints

    grid: GridSystem

    motion: MotionSystem

    design_principles: list[DesignPrinciple]

    component_guidelines: list[ComponentGuideline]