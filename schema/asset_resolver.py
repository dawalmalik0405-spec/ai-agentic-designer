from pydantic import BaseModel
from typing import List
from enum import Enum

from schema.asset import AssetRequirement, AssetType, SourceStrategy, AssetPriority


class ResolutionPath(str, Enum):
    """Asset resolution paths in the workflow."""
    STOCK = "stock"          # Search API → Candidates → Selector → Downloader
    GENERATE = "generate"    # Image Model
    ICON_CSS = "icon_css"    # Icon/CSS Libraries
    CLIENT = "client"        # Client-provided assets


class ResolvedAsset(BaseModel):
    """Asset after resolver has decided the path and strategy."""
    
    requirement: AssetRequirement
    resolution_path: ResolutionPath
    reasoning: str  # Why this path was chosen
    confidence: float  # 0.0-1.0 confidence in this choice
    
    # Path-specific instructions
    search_keywords: List[str] | None = None  # For STOCK path
    generation_prompt: str | None = None      # For GENERATE path
    library_name: str | None = None           # For ICON_CSS path
    

class ResolverOutput(BaseModel):
    """Output of the Asset Resolver."""
    
    total_assets: int
    resolved_assets: List[ResolvedAsset]
    
    # Statistics
    stock_count: int
    generate_count: int
    icon_css_count: int
    client_count: int
