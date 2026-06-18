from __future__ import annotations

from pydantic import BaseModel


class ExtractedFrame(BaseModel):

    frame_id: str

    source_video_id: str

    frame_number: int

    frame_path: str


class ExtractedVideo(BaseModel):

    video_id: str

    video_path: str

    frame_count: int

    frames: list[ExtractedFrame]


class FrameExtractionOutput(BaseModel):

    videos: list[ExtractedVideo]