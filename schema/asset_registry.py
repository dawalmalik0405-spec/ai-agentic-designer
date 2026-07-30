from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum

from schema.asset import AssetType


class AssetEntry(BaseModel):
    """Single entry in the asset registry."""
    
    asset_id: str
    asset_type: AssetType
    
    # File information
    file_path: str
    file_size: int
    file_format: str  # .png, .jpg, .svg, etc.
    
    # Metadata
    page_name: str
    section_name: str
    purpose: str
    
    # Source information
    source_provider: str  # pollinations, internet, icon_library, etc.
    source_url: Optional[str] = None
    
    # Quality/dimensions
    width: int
    height: int
    aspect_ratio: float
    
    # Timestamps
    created_at: str
    indexed_at: str
    
    # Tags for searching
    tags: List[str] = []
    

class RegistryQuery(BaseModel):
    """Query parameters for asset lookup."""
    
    asset_id: Optional[str] = None
    asset_type: Optional[AssetType] = None
    page_name: Optional[str] = None
    section_name: Optional[str] = None
    tags: Optional[List[str]] = None  # Match any tag


class QueryResult(BaseModel):
    """Results of a registry query."""
    
    total_matches: int
    assets: List[AssetEntry]


class RegistryStats(BaseModel):
    """Registry statistics."""
    
    total_assets: int
    by_type: Dict[str, int]  # AssetType -> count
    by_provider: Dict[str, int]  # provider -> count
    total_storage_bytes: int
    asset_ids: List[str]
