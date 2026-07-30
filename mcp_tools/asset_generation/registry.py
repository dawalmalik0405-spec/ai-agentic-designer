"""
Asset Registry - Centralized store for all generated/sourced assets.

Provides:
- Fast lookup by asset_id for Code Agent
- Querying by type, page, section, tags
- Persistence to disk
- Statistics and metadata
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from schema.asset_registry import (
    AssetEntry,
    RegistryQuery,
    QueryResult,
    RegistryStats,
)
from schema.asset import AssetType
from schema.asset_processor import ProcessedAsset, ProcessingPhase


logger = logging.getLogger(__name__)


class AssetRegistry:
    """Central registry for all generated/sourced assets."""
    
    def __init__(self, registry_path: str = "assets/registry.json"):
        self.registry_path = registry_path
        self.registry_dir = os.path.dirname(registry_path)
        
        # In-memory storage
        self._assets: Dict[str, AssetEntry] = {}
        
        # Create registry directory if needed
        os.makedirs(self.registry_dir, exist_ok=True)
        
        # Load existing registry
        self.load()
    
    def register(self, processed_asset: ProcessedAsset) -> Optional[AssetEntry]:
        """
        Register a processed asset in the registry.
        
        Args:
            processed_asset: ProcessedAsset from the processor
            
        Returns:
            AssetEntry if successful, None if asset wasn't successfully processed
        """
        # Only register successfully processed assets
        if processed_asset.processing_phase != ProcessingPhase.VALIDATED:
            logger.warning(
                f"Skipping registration of non-validated asset: {processed_asset.asset_id}"
            )
            return None
        
        if not processed_asset.generated_asset:
            logger.warning(
                f"Skipping registration: no generated asset for {processed_asset.asset_id}"
            )
            return None
        
        gen_asset = processed_asset.generated_asset
        
        # Calculate aspect ratio
        aspect_ratio = gen_asset.width / gen_asset.height if gen_asset.height > 0 else 1.0
        
        # Extract file format
        file_format = os.path.splitext(processed_asset.file_path or "")[1] or ".png"
        
        # Create entry
        entry = AssetEntry(
            asset_id=processed_asset.asset_id,
            asset_type=processed_asset.asset_type,
            file_path=processed_asset.file_path,
            file_size=processed_asset.file_size or 0,
            file_format=file_format,
            page_name=self._extract_page_name(processed_asset),
            section_name=self._extract_section_name(processed_asset),
            purpose=self._extract_purpose(processed_asset),
            source_provider=gen_asset.provider,
            source_url=gen_asset.provider_asset_url,
            width=gen_asset.width,
            height=gen_asset.height,
            aspect_ratio=aspect_ratio,
            created_at=gen_asset.created_at or self._timestamp(),
            indexed_at=self._timestamp(),
            tags=self._generate_tags(processed_asset),
        )
        
        # Store in registry
        self._assets[entry.asset_id] = entry
        
        logger.info(
            "Asset registered",
            extra={
                "asset_id": entry.asset_id,
                "type": entry.asset_type.value,
                "file_path": entry.file_path,
            }
        )
        
        return entry
    
    def register_batch(self, processed_assets: List[ProcessedAsset]) -> int:
        """
        Register multiple processed assets.
        
        Args:
            processed_assets: List of ProcessedAsset
            
        Returns:
            Number of successfully registered assets
        """
        registered = 0
        for asset in processed_assets:
            if self.register(asset):
                registered += 1
        
        # Persist after batch
        self.save()
        
        logger.info(
            "Batch registration complete",
            extra={"registered": registered, "total": len(processed_assets)}
        )
        
        return registered
    
    def get(self, asset_id: str) -> Optional[AssetEntry]:
        """Get asset by ID."""
        return self._assets.get(asset_id)
    
    def get_by_page(self, page_name: str) -> List[AssetEntry]:
        """Get all assets for a page."""
        return [
            asset for asset in self._assets.values()
            if asset.page_name == page_name
        ]
    
    def get_by_type(self, asset_type: AssetType) -> List[AssetEntry]:
        """Get all assets of a specific type."""
        return [
            asset for asset in self._assets.values()
            if asset.asset_type == asset_type
        ]
    
    def query(self, query: RegistryQuery) -> QueryResult:
        """
        Query the registry with multiple filters.
        
        Args:
            query: RegistryQuery with optional filters
            
        Returns:
            QueryResult with matching assets
        """
        results = list(self._assets.values())
        
        if query.asset_id:
            results = [a for a in results if a.asset_id == query.asset_id]
        
        if query.asset_type:
            results = [a for a in results if a.asset_type == query.asset_type]
        
        if query.page_name:
            results = [a for a in results if a.page_name == query.page_name]
        
        if query.section_name:
            results = [a for a in results if a.section_name == query.section_name]
        
        if query.tags:
            # Match any tag (OR logic)
            results = [
                a for a in results
                if any(tag in a.tags for tag in query.tags)
            ]
        
        return QueryResult(
            total_matches=len(results),
            assets=results,
        )
    
    def get_all_asset_ids(self) -> List[str]:
        """Get list of all registered asset IDs."""
        return list(self._assets.keys())
    
    def get_stats(self) -> RegistryStats:
        """Get registry statistics."""
        by_type: Dict[str, int] = {}
        by_provider: Dict[str, int] = {}
        total_size = 0
        
        for asset in self._assets.values():
            # Count by type
            type_key = asset.asset_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # Count by provider
            provider_key = asset.source_provider
            by_provider[provider_key] = by_provider.get(provider_key, 0) + 1
            
            # Total size
            total_size += asset.file_size
        
        return RegistryStats(
            total_assets=len(self._assets),
            by_type=by_type,
            by_provider=by_provider,
            total_storage_bytes=total_size,
            asset_ids=self.get_all_asset_ids(),
        )
    
    def save(self) -> bool:
        """Persist registry to disk."""
        try:
            data = {
                "assets": {
                    asset_id: entry.model_dump()
                    for asset_id, entry in self._assets.items()
                },
                "saved_at": self._timestamp(),
                "version": "1.0",
            }
            
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(
                "Registry saved",
                extra={"path": self.registry_path, "assets": len(self._assets)}
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            return False
    
    def load(self) -> bool:
        """Load registry from disk."""
        if not os.path.exists(self.registry_path):
            logger.info(f"Registry file not found: {self.registry_path}")
            return False
        
        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)
            
            self._assets = {}
            for asset_id, entry_data in data.get("assets", {}).items():
                try:
                    entry = AssetEntry(**entry_data)
                    self._assets[asset_id] = entry
                except Exception as e:
                    logger.warning(f"Failed to parse asset entry {asset_id}: {e}")
            
            logger.info(
                "Registry loaded",
                extra={"path": self.registry_path, "assets": len(self._assets)}
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all assets from registry."""
        self._assets.clear()
        logger.info("Registry cleared")
    
    def export_for_code_agent(self) -> Dict[str, str]:
        """
        Export registry as a map for the Code Agent to use.
        Format: {asset_id -> file_path}
        
        Used by Code Agent to inject asset references into generated code.
        """
        return {asset_id: asset.file_path for asset_id, asset in self._assets.items()}
    
    def _extract_page_name(self, processed_asset: ProcessedAsset) -> str:
        """Extract page name from asset ID or metadata."""
        # Try to extract from asset_id (format: page_section_...)
        parts = processed_asset.asset_id.split("_")
        return parts[0] if parts else "unknown"
    
    def _extract_section_name(self, processed_asset: ProcessedAsset) -> str:
        """Extract section name from asset ID."""
        parts = processed_asset.asset_id.split("_")
        return parts[1] if len(parts) > 1 else "unknown"
    
    def _extract_purpose(self, processed_asset: ProcessedAsset) -> str:
        """Extract purpose from asset ID."""
        # Try to reconstruct from asset_id
        parts = processed_asset.asset_id.split("_")
        return " ".join(parts).title() if parts else "Asset"
    
    def _generate_tags(self, processed_asset: ProcessedAsset) -> List[str]:
        """Generate searchable tags for the asset."""
        tags = []
        
        # Asset type tag
        tags.append(processed_asset.asset_type.value)
        
        # Page and section tags
        page = self._extract_page_name(processed_asset)
        section = self._extract_section_name(processed_asset)
        if page != "unknown":
            tags.append(page)
        if section != "unknown":
            tags.append(section)
        
        # Provider tag
        tags.append(processed_asset.resolution_path)
        
        # Path tags
        tags.extend(processed_asset.attempted_paths)
        
        return list(dict.fromkeys(tags))  # Deduplicate while preserving order
    
    def _timestamp(self) -> str:
        """Get current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
