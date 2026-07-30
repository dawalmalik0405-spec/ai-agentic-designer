from pydantic import BaseModel
from typing import List
from enum import Enum

from schema.asset import AssetType
from schema.asset_gen import GeneratedAsset


class ProcessingPhase(str, Enum):
    """Stages of asset processing."""
    RESOLVED = "resolved"           # From resolver
    ATTEMPTING_PATH = "attempting_path"  # Currently processing
    DOWNLOADED = "downloaded"        # Retrieved/generated
    VALIDATED = "validated"         # Quality checks passed
    FAILED = "failed"               # Processing failed


class ProcessedAsset(BaseModel):
    """Asset after processing through its resolution path."""
    
    asset_id: str
    asset_type: AssetType
    
    # Path execution results
    generated_asset: GeneratedAsset | None = None  # Final output
    
    # Metadata
    processing_phase: ProcessingPhase
    resolution_path: str  # stock, generate, icon_css, client
    attempted_paths: List[str] = []  # Fallback chain
    
    # Quality/validation
    file_path: str | None = None
    file_size: int | None = None
    validation_passed: bool = False
    validation_errors: List[str] = []
    
    # Timing
    processing_time_ms: float = 0.0
    created_at: str | None = None
    

class ProcessorOutput(BaseModel):
    """Output of the Asset Processor."""
    
    total_assets: int
    processed_assets: List[ProcessedAsset]
    
    # Statistics
    successful: int
    failed: int
    skipped: int
    
    # Summary
    total_file_size_bytes: int = 0
    average_processing_time_ms: float = 0.0
