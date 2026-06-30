from typing import TypedDict

from schema.architect import ArchitectOutput
from schema.research import ResearchOutput
from schema.desighn import DesignSystemOutput
from schema.page_d import PageDesignOutput
from schema.asset import AssetOutput
from schema.asset_gen import GeneratedAssetOutput
from schema.frame import FrameExtractionOutput


class WebsiteBuilderState(TypedDict):

    user_prompt: str

    selected_style: str

    architect_output: ArchitectOutput | None

    research_output: ResearchOutput | None

    design_system_output: DesignSystemOutput | None

    page_design_output: PageDesignOutput | None

    asset_output: AssetOutput | None

    generated_asset_output: GeneratedAssetOutput | None

    frame_extraction_output: FrameExtractionOutput | None

    generated_code: str | None