from pydantic import BaseModel
from typing import List
from enum import Enum

from schema.asset import AssetType


class GenerationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class GeneratedAsset(BaseModel):

    asset_id: str

    asset_type: AssetType

    file_path: str

    provider: str

    status: GenerationStatus

    width: int

    height: int

    source_asset_id: str | None = None

    error: str | None = None

    created_at: str

    provider_asset_url: str | None


class GeneratedAssetOutput(BaseModel):

    assets: List[GeneratedAsset]