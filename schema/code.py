from pydantic import BaseModel

from schema.architect import ArchitectOutput
from schema.research import ResearchOutput
from schema.desighn import DesignSystemOutput
from schema.page_d import PageDesignOutput
from schema.asset import AssetOutput
from schema.asset_gen import GeneratedAssetOutput

from schema.motion import MotionSpecification





class CodeGenerationInput(BaseModel):
    user_prompt: str

    architect_output: ArchitectOutput
    research_output: ResearchOutput
    design_output: DesignSystemOutput
    page_output: PageDesignOutput

    asset_output: AssetOutput
    motion_output: MotionSpecification

    generated_asset_output: GeneratedAssetOutput




class GeneratedFile(BaseModel):
    path: str
    content: str
    description: str | None = None
    language: str | None = None


class CodeGenerationOutput(BaseModel):
    files: list[GeneratedFile]
    build_status: str | None = None
    preview_url: str | None = None