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
        self.video_provider_name = "pollinations"
        self.video_provider = self.provider
        self.storage = AssetStorage()


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
    
    async def generate_video_asset(
        self,
        asset: AssetRequirement
    ) -> list[GeneratedAsset]:
        
        if not asset.prompt:
            raise ValueError(
                f"Asset {asset.asset_id} has no prompt"
            )

        image_url = await self.provider.generate_image_url(
            asset.prompt,
            width=asset.width,
            height=asset.height
        )

        image_bytes = await self.provider.generate_image(
            asset.prompt,
            width=asset.width,
            height=asset.height
        )


        source_filename = (
            f"{asset.asset_id}_source.jpg"
        )

        source_path = await self.storage.save_image(
            image_bytes,
            source_filename
        )


        video_prompt = (
            asset.animation_description
            or asset.prompt
        )

        video_bytes = await self.provider.generate_video(
            prompt=video_prompt,
            image_url=image_url
        )
        video_provider = "pollinations"

        video_path = await self.storage.save_video(
            video_bytes,
            asset.output_filename
        )


        source_asset = GeneratedAsset(
            asset_id=f"{asset.asset_id}_source",
            asset_type=AssetType.IMAGE,
            file_path=source_path,
            provider="pollinations",
            status=GenerationStatus.SUCCESS,
            width=asset.width,
            height=asset.height,
            created_at=self._created_at(),
            provider_asset_url=None
        )



        video_asset = GeneratedAsset(
            asset_id=asset.asset_id,
            asset_type=AssetType.VIDEO,
            file_path=video_path,
            provider=video_provider,
            status=GenerationStatus.SUCCESS,
            width=asset.width,
            height=asset.height,
            source_asset_id=source_asset.asset_id,
            created_at=self._created_at(),
            provider_asset_url=None
        )


        return [
            source_asset,
            video_asset
        ]
    

    async def execute_asset(
        self,
        asset: AssetRequirement
    ) -> list[GeneratedAsset]:

        if (
            not asset.generation_required
            or asset.source_strategy != SourceStrategy.GENERATE
        ):
            return [
                self.skipped_asset(
                    asset
                )
            ]
        
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
        

        if asset.asset_type == AssetType.VIDEO:

            try:
                return await self.generate_video_asset(
                    asset
                )
            except Exception as error:
                return [
                    self.failed_asset(
                        asset,
                        error
                    )
                ]
        
        
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


    


