from __future__ import annotations

import logging
from datetime import datetime, timezone

from schema.asset import (
    AssetRequirement,
    AssetType,
    SourceStrategy
)

from schema.asset_gen import (
    GeneratedAsset,
    GeneratedAssetOutput,
    GenerationStatus
)

from .providers.pollinations_provider import (
    PollinationsProvider
)

from .storage.asset_storage import (
    AssetStorage
)




logger = logging.getLogger(__name__)


class AssetExecutor:

    def __init__(self):

        self.provider = PollinationsProvider()
        self.storage = AssetStorage()
        
        # Internet providers
        from .providers.search_provider import SearchProvider
        from .providers.asset_downloader import AssetDownloader
        from .providers.candidate_selector import CandidateSelector
        
        self.search_provider = SearchProvider()
        self.asset_downloader = AssetDownloader(storage=self.storage)
        self.candidate_selector = CandidateSelector()


    async def connect(self):

        await self.provider.connect()

    async def close(self):

        await self.provider.close()


    def _created_at(
        self
    ) -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()


    def skipped_asset(
        self,
        asset: AssetRequirement
    ) -> GeneratedAsset:

        return GeneratedAsset(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type,
            file_path=(
                f"{asset.source_strategy.value}://"
                f"{asset.output_filename}"
            ),
            provider=asset.source_strategy.value,
            status=GenerationStatus.SKIPPED,
            width=asset.width,
            height=asset.height,
            created_at=self._created_at(),
            provider_asset_url=None
        )


    def failed_asset(
        self,
        asset: AssetRequirement,
        error: Exception
    ) -> GeneratedAsset:

        logger.warning(
            "Asset generation degraded gracefully",
            extra={
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type.value,
                "provider": "pollinations",
                "error_type": type(error).__name__,
                "error": str(error)
            }
        )

        return GeneratedAsset(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type,
            file_path="",
            provider="pollinations",
            status=GenerationStatus.FAILED,
            width=asset.width,
            height=asset.height,
            error=str(error),
            created_at=self._created_at(),
            provider_asset_url=None
        )



    async def generate_image_asset(
        self,
        asset: AssetRequirement
    ) -> GeneratedAsset:
        

        if not asset.prompt:
            raise ValueError(
                f"Asset {asset.asset_id} has no prompt"
            )
        
        image_bytes = await self.provider.generate_image(
            asset.prompt,
            width=asset.width,
            height=asset.height
        )

        image_path = await self.storage.save_image(
            image_bytes,
            asset.output_filename
        )

        return GeneratedAsset(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type,
            file_path=image_path,
            provider="pollinations",
            status=GenerationStatus.SUCCESS,
            width=asset.width,
            height=asset.height,
            created_at=self._created_at(),
            provider_asset_url=None
        )
    

    async def generate_internet_asset(
        self,
        asset: AssetRequirement
    ) -> GeneratedAsset:
        if not asset.prompt:
            raise ValueError(f"Asset {asset.asset_id} has no prompt for search")
            
        orientation = "landscape"
        if asset.height > asset.width * 1.2:
            orientation = "portrait"
        elif abs(asset.width - asset.height) < asset.width * 0.2:
            orientation = "squarish"
            
        keywords = [asset.prompt]
        if asset.style_keywords:
            keywords.extend(asset.style_keywords)
            
        # Import the search query schema
        from .providers.search_provider import SearchQuery
        query = SearchQuery(
            keywords=keywords,
            width_min=int(asset.width * 0.8),
            height_min=int(asset.height * 0.8),
            orientation=orientation,
            max_results=10
        )
        
        candidates = await self.search_provider.search(query, provider="unsplash")
        
        if not candidates:
            raise RuntimeError(f"No internet candidates found for {asset.asset_id}")
            
        best = self.candidate_selector.select_best(asset, candidates)
        if not best:
             raise RuntimeError(f"No suitable candidate found for {asset.asset_id} from {len(candidates)} results")
             
        return await self.asset_downloader.download(
            asset_id=asset.asset_id,
            candidate=best,
            output_filename=asset.output_filename,
            asset_type=asset.asset_type,
            width=asset.width,
            height=asset.height
        )
    

    async def execute_asset(
        self,
        asset: AssetRequirement
    ) -> list[GeneratedAsset]:

        if (
            not asset.generation_required
            or asset.source_strategy not in {SourceStrategy.GENERATE, SourceStrategy.INTERNET}
        ):
            return [
                self.skipped_asset(
                    asset
                )
            ]
        
        if asset.source_strategy == SourceStrategy.INTERNET:
            try:
                result = await self.generate_internet_asset(asset)
            except Exception as error:
                result = self.failed_asset(asset, error)
            return [result]
        
        if asset.asset_type in {
            AssetType.IMAGE,
            AssetType.ILLUSTRATION,
            AssetType.SVG_DIAGRAM,
            AssetType.BACKGROUND,
        }:

            try:
                result = await self.generate_image_asset(
                    asset
                )
            except Exception as error:
                result = self.failed_asset(
                    asset,
                    error
                )

            return [result]
        
        return []
    

    async def execute_assets(
        self,
        assets: list[AssetRequirement]
    ) -> list[GeneratedAsset]:

        generated_assets: list[GeneratedAsset] = []

        for asset in assets:

            results = await self.execute_asset(
                asset
            )

            generated_assets.extend(
                results
            )

        return generated_assets
    


    async def execute_assets_output(
        self,
        assets: list[AssetRequirement]
    ) -> GeneratedAssetOutput:

        generated_assets = await self.execute_assets(
            assets
        )

        required_generated_assets = [
            asset
            for asset in assets
            if (
                asset.generation_required
                and asset.source_strategy == SourceStrategy.GENERATE
            )
        ]
        successful_generated_assets = [
            asset
            for asset in generated_assets
            if asset.status == GenerationStatus.SUCCESS
        ]

        if required_generated_assets and not successful_generated_assets:
            failed_errors = [
                f"{asset.asset_id}: {asset.error}"
                for asset in generated_assets
                if asset.status == GenerationStatus.FAILED
            ]
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Asset generation failed for every required generated asset. "
                + "; ".join(failed_errors[:10])
            )

        return GeneratedAssetOutput(
            assets=generated_assets
        )


    


