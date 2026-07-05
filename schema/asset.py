from pydantic import BaseModel
from typing import List
from enum import Enum


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    ICON = "icon"
    LOGO = "logo"
    LOTTIE = "lottie"
    ILLUSTRATION = "illustration"
    SVG_DIAGRAM = "svg_diagram"
    BACKGROUND = "background"


class AssetPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceStrategy(str, Enum):
    GENERATE = "generate"
    INTERNET = "internet"
    ICON_LIBRARY = "icon_library"
    LOGO_LIBRARY = "logo_library"
    CLIENT_PROVIDED = "client_provided"


class AssetRequirement(BaseModel):

    asset_id: str

    page_name: str

    section_name: str

    purpose: str

    asset_type: AssetType

    priority: AssetPriority

    source_strategy: SourceStrategy

    generation_required: bool

    prompt: str | None = None

    negative_prompt: str | None = None

    style_keywords: List[str] | None = None

    animation_required: bool = False

    animation_description: str | None = None

    width: int

    height: int

    format: str

    output_filename: str

    source_output_filename: str | None = None


class AssetOutput(BaseModel):

    project_style: str

    design_theme: str

    assets: List[AssetRequirement]