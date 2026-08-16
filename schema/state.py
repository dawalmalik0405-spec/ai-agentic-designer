from typing import TypedDict

from schema.architect import ArchitectOutput
from schema.research import ResearchOutput
from schema.desighn import DesignSystemOutput
from schema.page_d import PageDesignOutput
from schema.code import CodeGenerationOutput
from schema.asset import AssetOutput
from schema.asset_gen import GeneratedAssetOutput
from schema.asset_injection import ApprovedAsset, AssetInjectionOutput
from schema.add_page import AddPageOutput
from schema.motion import MotionSpecification


class WebsiteBuilderState(TypedDict):

    user_prompt: str

    selected_style: str

    architect_output: ArchitectOutput | None

    research_output: ResearchOutput | None

    design_system_output: DesignSystemOutput | None

    page_design_output: PageDesignOutput | None

    page_code_output: CodeGenerationOutput | None 



class AssetGenerationState(TypedDict):
    design_system_output: DesignSystemOutput
    page_design_output: PageDesignOutput
    page_code_output: CodeGenerationOutput

    asset_output: AssetOutput | None
    generated_asset_output: GeneratedAssetOutput | None



class MotionGenerationState(TypedDict):
    design_system_output: DesignSystemOutput

    page_design_output: PageDesignOutput

    page_code_output: CodeGenerationOutput

    generated_asset_output: GeneratedAssetOutput

    motion_output: MotionSpecification | None

    final_page_code_output: CodeGenerationOutput | None


class AssetInjectionState(TypedDict):
    project_id: str
    generated_site_dir: str | None
    target_page_name: str | None
    approved_assets: list[ApprovedAsset] | None
    injection_output: AssetInjectionOutput | None
    dev_server_status: str | None
    preview_url: str | None
    log_tail: list[str]


class AddPageState(TypedDict):
    project_id: str
    page_name: str
    user_prompt: str
    selected_style: str
    generated_site_dir: str | None

    existing_architect_output: ArchitectOutput
    existing_research_output: ResearchOutput
    existing_design_system_output: DesignSystemOutput
    existing_page_design_output: PageDesignOutput

    architect_output: ArchitectOutput | None
    research_output: ResearchOutput | None
    design_system_output: DesignSystemOutput | None
    page_design_output: PageDesignOutput | None
    page_code_output: CodeGenerationOutput | None
    add_page_output: AddPageOutput | None




class EditState(TypedDict):

    project_id: str

    user_instruction: str

    selected_files: list[str]

    edit_intent: dict | None

    dependency_report: dict | None

    edit_result: CodeGenerationOutput | None

    build_success: bool | None
