from __future__ import annotations

from schema.asset import AssetType
from schema.asset_gen import GeneratedAssetOutput

from schema.frame import (
    FrameExtractionOutput
)

from mcp_tools.frame_extraction.extractor import (
    FrameExtractor
)

from mcp_tools.frame_extraction.storage import (
    FrameStorage
)


class FrameExtractionAgent:

    def __init__(self):

        self.extractor = FrameExtractor()

        self.storage = FrameStorage()

    async def extract(
        self,
        generated_assets: GeneratedAssetOutput
    ) -> FrameExtractionOutput:

        videos = []

        for asset in generated_assets.assets:

            if asset.asset_type != AssetType.VIDEO:
                continue

            extracted_video = (
                await self.extractor.extract_video(
                    video_id=asset.asset_id,
                    video_path=asset.file_path
                )
            )

            videos.append(
                extracted_video
            )

        output = FrameExtractionOutput(
            videos=videos
        )

        self.storage.save_metadata(
            output.model_dump()
        )

        return output