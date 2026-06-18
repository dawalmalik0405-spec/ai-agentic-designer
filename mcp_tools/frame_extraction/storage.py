from __future__ import annotations

import json
import os


class FrameStorage:

    def __init__(
        self,
        asset_root: str = "assets"
    ):

        self.asset_root = asset_root

        self.frames_dir = os.path.join(
            asset_root,
            "frames"
        )

        self.metadata_dir = os.path.join(
            asset_root,
            "metadata"
        )

        os.makedirs(
            self.frames_dir,
            exist_ok=True
        )

        os.makedirs(
            self.metadata_dir,
            exist_ok=True
        )

    def create_video_directory(
        self,
        video_id: str
    ) -> str:

        path = os.path.join(
            self.frames_dir,
            video_id
        )

        os.makedirs(
            path,
            exist_ok=True
        )

        return path

    def save_metadata(
        self,
        metadata: dict,
        filename: str = "frame_extraction.json"
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
    

storage = FrameStorage()

path = storage.create_video_directory(
    "castle_intro"
)

print(path)