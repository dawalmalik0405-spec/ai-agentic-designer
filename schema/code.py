from pydantic import BaseModel

from architect import ArchitectOutput
from research import ResearchOutput
from desighn import DesignSystemOutput
from page_d import PageDesignOutput
from asset import AssetOutput
from asset_gen import GeneratedAssetOutput
from frame import FrameExtractionOutput





class CodeGenerationInput(BaseModel):

    user_prompt: str

    architect_output: ArchitectOutput

    research_output: ResearchOutput

    design_output: DesignSystemOutput

    page_output: PageDesignOutput

    asset_output: AssetOutput

    generated_asset_output: GeneratedAssetOutput

    frame_extraction_output: FrameExtractionOutput



class GeneratedFile(BaseModel):

    path: str

    content: str

    description: str | None = None


class CodeGenerationOutput(BaseModel):

    files: list[GeneratedFile]