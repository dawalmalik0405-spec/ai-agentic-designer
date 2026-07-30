"""
Asset Orchestrator - Coordinates the complete asset generation pipeline.

Flow:
1. Asset Requirements (from Asset Agent) → Resolver
2. Resolved Assets → Processor  
3. Processed Assets → Registry
4. Registry exports to Code Agent

This is the main entry point for the asset generation system.
"""

import logging
from typing import Optional

from schema.asset import AssetOutput
from schema.asset_registry import RegistryStats

from mcp_tools.asset_generation.resolver import AssetResolver
from mcp_tools.asset_generation.processor import AssetProcessor
from mcp_tools.asset_generation.registry import AssetRegistry


logger = logging.getLogger(__name__)


class AssetOrchestrator:
    """Main orchestrator for the asset generation pipeline."""
    
    def __init__(self, registry_path: str = "assets/registry.json"):
        self.resolver = AssetResolver()
        self.processor = AssetProcessor()
        self.registry = AssetRegistry(registry_path)
    
    async def orchestrate(self, asset_output: AssetOutput) -> dict:
        """
        Run the complete asset pipeline.
        
        Args:
            asset_output: AssetOutput from Asset Agent (requirements)
            
        Returns:
            Dictionary with pipeline results and registry stats
        """
        logger.info("Starting asset orchestration pipeline")
        
        try:
            # Step 1: Resolve assets to paths
            logger.info("Step 1: Resolving assets...")
            resolver_output = self.resolver.resolve(asset_output)
            logger.info(
                "Resolution complete",
                extra={
                    "stock": resolver_output.stock_count,
                    "generate": resolver_output.generate_count,
                    "icon_css": resolver_output.icon_css_count,
                    "client": resolver_output.client_count,
                }
            )
            
            # Step 2: Process assets through their paths
            logger.info("Step 2: Processing assets...")
            processor_output = await self.processor.process(resolver_output)
            logger.info(
                "Processing complete",
                extra={
                    "successful": processor_output.successful,
                    "failed": processor_output.failed,
                    "skipped": processor_output.skipped,
                    "avg_time_ms": processor_output.average_processing_time_ms,
                }
            )
            
            # Step 3: Register processed assets
            logger.info("Step 3: Registering assets...")
            registered_count = self.registry.register_batch(processor_output.processed_assets)
            logger.info(f"Registered {registered_count} assets")
            
            # Get registry stats
            stats = self.registry.get_stats()
            logger.info(
                "Pipeline complete",
                extra={
                    "total_registered": stats.total_assets,
                    "total_storage_mb": stats.total_storage_bytes / (1024 * 1024),
                }
            )
            
            return {
                "status": "success",
                "resolver_output": {
                    "total": resolver_output.total_assets,
                    "by_path": {
                        "stock": resolver_output.stock_count,
                        "generate": resolver_output.generate_count,
                        "icon_css": resolver_output.icon_css_count,
                        "client": resolver_output.client_count,
                    }
                },
                "processor_output": {
                    "total": processor_output.total_assets,
                    "successful": processor_output.successful,
                    "failed": processor_output.failed,
                    "skipped": processor_output.skipped,
                    "avg_processing_time_ms": processor_output.average_processing_time_ms,
                },
                "registry_stats": stats.model_dump(),
                "asset_map": self.registry.export_for_code_agent(),
            }
        
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }
    
    def get_registry_stats(self) -> RegistryStats:
        """Get current registry statistics."""
        return self.registry.get_stats()
    
    def get_asset_by_id(self, asset_id: str):
        """Look up asset by ID."""
        return self.registry.get(asset_id)
    
    def get_assets_for_page(self, page_name: str):
        """Get all assets for a specific page."""
        return self.registry.get_by_page(page_name)
    
    def export_asset_map(self) -> dict:
        """Export asset map for Code Agent."""
        return self.registry.export_for_code_agent()
    
    def clear_registry(self) -> None:
        """Clear all assets from registry."""
        self.registry.clear()
