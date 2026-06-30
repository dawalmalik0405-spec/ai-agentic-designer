from pydantic import BaseModel

from schema.architect import ArchitectOutput
from schema.research import ResearchOutput
from schema.desighn import DesignSystemOutput
from schema.page_d import PageDesignOutput
from schema.asset import AssetOutput
from schema.asset_gen import GeneratedAssetOutput
from schema.frame import FrameExtractionOutput





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