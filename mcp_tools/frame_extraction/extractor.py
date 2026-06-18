from __future__ import annotations

import os

import cv2

from schema.frame import (
    ExtractedFrame,
    ExtractedVideo
)

from .storage import FrameStorage




class FrameExtractor:

    def __init__(
        self,
        sample_every_n_frames: int = 15
    ):

        self.sample_every_n_frames = (
            sample_every_n_frames
        )

        self.storage = FrameStorage()



    async def extract_video(
        self,
        video_id: str,
        video_path: str
    ) -> ExtractedVideo:
        

        cap = cv2.VideoCapture(
            video_path
        )

        frame_dir = (
            self.storage.create_video_directory(
                video_id
            )
        )


        frames = []

        frame_index = 0

        saved_frame_index = 0


        while True:

            success, frame = cap.read()

            if not success:
                break

            if (
                frame_index %
                self.sample_every_n_frames
                == 0
            ):

                filename = (
                    f"frame_{saved_frame_index:04d}.jpg"
                )

                frame_path = os.path.join(
                    frame_dir,
                    filename
                )

                cv2.imwrite(
                    frame_path,
                    frame
                )

                frames.append(

                    ExtractedFrame(
                        frame_id=(
                            f"{video_id}_{saved_frame_index}"
                        ),
                        source_video_id=video_id,
                        frame_number=saved_frame_index,
                        frame_path=frame_path
                    )
                )

                saved_frame_index += 1

            frame_index += 1

        cap.release()

        return ExtractedVideo(
            video_id=video_id,
            video_path=video_path,
            frame_count=len(frames),
            frames=frames
        )


import asyncio


async def main():

    extractor = FrameExtractor()

    result = await extractor.extract_video(
        video_id="test_video",
        video_path="assets/videos/test.mp4"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())