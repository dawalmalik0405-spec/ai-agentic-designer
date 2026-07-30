from __future__ import annotations

import logging

from schema.asset import AssetOutput
from schema.asset_gen import GeneratedAssetOutput

from mcp_tools.asset_generation.orchestrator import AssetOrchestrator


logger = logging.getLogger(__name__)


class GenerationAgent:
    """Agent that coordinates asset generation through the full pipeline."""

    def __init__(self):
        self.orchestrator = AssetOrchestrator()

    async def generate(
        self,
        asset_output: AssetOutput
    ) -> GeneratedAssetOutput:
        """
        Generate assets using the complete orchestrated pipeline:
        Resolver → Processor → Registry
        
        Args:
            asset_output: Asset requirements from Asset Agent
            
        Returns:
            GeneratedAssetOutput with processed and registered assets
        """
        
        logger.info(f"Generating assets for {len(asset_output.assets)} requirements")
        
        # Run the orchestrated pipeline
        pipeline_result = await self.orchestrator.orchestrate(asset_output)
        
        if pipeline_result["status"] != "success":
            logger.error(f"Asset generation pipeline failed: {pipeline_result.get('error')}")
            return GeneratedAssetOutput(assets=[])
        
        # Build GeneratedAssetOutput from registry
        registry_stats = self.orchestrator.get_registry_stats()
        registered_assets = []
        
        for asset_id in registry_stats.asset_ids:
            entry = self.orchestrator.get_asset_by_id(asset_id)
            if entry:
                # Convert registry entry back to GeneratedAsset format
                from schema.asset_gen import GeneratedAsset, GenerationStatus
                
                gen_asset = GeneratedAsset(
                    asset_id=entry.asset_id,
                    asset_type=entry.asset_type,
                    file_path=entry.file_path,
                    provider=entry.source_provider,
                    status=GenerationStatus.SUCCESS,
                    width=entry.width,
                    height=entry.height,
                    created_at=entry.created_at,
                    provider_asset_url=entry.source_url,
                )
                registered_assets.append(gen_asset)
        
        logger.info(f"Generation complete: {len(registered_assets)} assets registered")
        
        return GeneratedAssetOutput(assets=registered_assets)
