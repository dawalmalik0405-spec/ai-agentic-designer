from __future__ import annotations

from schema.asset import (
    AssetRequirement,
    AssetType
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




class AssetExecutor:

    def __init__(self):

        self.provider = PollinationsProvider()
        self.storage = AssetStorage()


    async def connect(self):

        await self.provider.connect()

    async def close(self):

        await self.provider.close()



    async def generate_image_asset(
        self,
        asset: AssetRequirement
    ) -> GeneratedAsset:
        

        if not asset.prompt:
            raise ValueError(
                f"Asset {asset.asset_id} has no prompt"
            )
        
        image_bytes = await self.provider.generate_image(
            asset.prompt
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
            height=asset.height
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
            asset.prompt
        )

        image_bytes = await self.provider.generate_image(
            asset.prompt
        )


        source_filename = (
            f"{asset.asset_id}_source.jpg"
        )

        source_path = await self.storage.save_image(
            image_bytes,
            source_filename
        )


        video_bytes = await self.provider.generate_video(
            prompt=(
                asset.animation_description
                or asset.prompt
            ),
            image_url=image_url
        )

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
            height=asset.height
        )



        video_asset = GeneratedAsset(
            asset_id=asset.asset_id,
            asset_type=AssetType.VIDEO,
            file_path=video_path,
            provider="pollinations",
            status=GenerationStatus.SUCCESS,
            width=asset.width,
            height=asset.height,
            source_asset_id=source_asset.asset_id
        )


        return [
            source_asset,
            video_asset
        ]
    

    async def execute_asset(
        self,
        asset: AssetRequirement
    ) -> list[GeneratedAsset]:
        
        if asset.asset_type == AssetType.IMAGE:

            result = await self.generate_image_asset(
                asset
            )

            return [result]
        

        if asset.asset_type == AssetType.VIDEO:

            return await self.generate_video_asset(
                asset
            )
        
        
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

        return GeneratedAssetOutput(
            assets=generated_assets
        )


    


