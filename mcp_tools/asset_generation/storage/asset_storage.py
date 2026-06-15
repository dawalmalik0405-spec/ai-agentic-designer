from __future__ import annotations

import aiohttp
import json
import os


class AssetStorage:

    def __init__(
        self,
        asset_root: str = "assets"
    ):

        self.asset_root = asset_root

        self.images_dir = os.path.join(
            asset_root, 
            "images"
        )

        self.videos_dir = os.path.join(
            asset_root,
            "videos"
        )

        self.metadata_dir = os.path.join(
            asset_root,
            "metadata"
        )

        os.makedirs(
            self.images_dir,
            exist_ok=True
        )

        os.makedirs(
            self.videos_dir,
            exist_ok=True
        )

        os.makedirs(
            self.metadata_dir,
            exist_ok=True
        )


    async def save_image(
        self,
        image_bytes: bytes,
        filename: str
    ) -> str:

        path = os.path.join(
            self.images_dir,
            filename
        )

        with open(
            path,
            "wb"
        ) as f:

            f.write(image_bytes)

        return path
    


    async def save_video(
        self,
        video_bytes: bytes,
        filename: str
    ) -> str:

        path = os.path.join(
            self.videos_dir,
            filename
        )

        with open(
            path,
            "wb"
        ) as f:

            f.write(video_bytes)

        return path
    


    def save_metadata(
        self,
        metadata: dict,
        filename: str = "generated_assets.json"
    ) -> str:

        path = os.path.join(
            self.metadata_dir,
            filename
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                metadata,
                f,
                indent=2,
                ensure_ascii=False
            )

        return path