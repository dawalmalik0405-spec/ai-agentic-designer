from pydantic import BaseModel


class ApprovedAsset(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    purpose: str = ""
    url: str
    page_name: str | None = None
    section_name: str | None = None
    dimensions: str | None = None


class AssetInjectionFileResult(BaseModel):
    path: str
    status: str
    injected_assets: list[str] = []
    error: str | None = None


class AssetInjectionOutput(BaseModel):
    status: str
    updated_files: list[str] = []
    injected_assets: list[str] = []
    file_results: list[AssetInjectionFileResult] = []
    errors: list[str] = []
    dev_server_status: str | None = None
    preview_url: str | None = None
    log_tail: list[str] = []
