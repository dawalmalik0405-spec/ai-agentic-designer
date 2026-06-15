from __future__ import annotations

import base64
import json

from mcp_tools.initialize_mcps import create_mcp_client

from ..storage.asset_storage import AssetStorage


class PollinationsProvider:

    def __init__(self):

        self.client = create_mcp_client(
            allowed_servers=["pollinations"]
        )

        self.session = None

    async def connect(self):

        await self.client.create_all_sessions()

        self.session = self.client.get_session(
            "pollinations"
        )

    async def close(self):

        await self.client.close_all_sessions()

    async def generate_image_url(
        self,
        prompt: str
    ) -> str:

        result = await self.session.call_tool(
            "generateImageUrl",
            {
                "prompt": prompt
            }
        )

        for item in result.content:

            if hasattr(item, "text"):

                data = json.loads(
                    item.text
                )

                image_url = data.get(
                    "imageUrl"
                )

                if image_url:
                    return image_url

        raise ValueError(
            "No image URL returned."
        )

    async def generate_video(
        self,
        prompt: str,
        image_url: str,
        duration: int = 6,
        aspect_ratio: str = "16:9"
    ) -> bytes:

        result = await self.session.call_tool(
            "generateVideo",
            {
                "prompt": prompt,
                "model": "ltx-2",
                "duration": duration,
                "aspectRatio": aspect_ratio,
                "image": image_url
            }
        )

        for item in result.content:

            if hasattr(item, "resource"):

                return base64.b64decode(
                    item.resource.blob
                )

        raise ValueError(
            "No video resource returned."
        )
    

    async def generate_image(
        self,
        prompt: str
    ) -> bytes:

        result = await self.session.call_tool(
            "generateImage",
            {
                "prompt": prompt
            }
        )

        for item in result.content:

            if hasattr(item, "data"):

                return base64.b64decode(
                    item.data
                )

        raise ValueError(
            "No image returned."
        )



# import asyncio


# async def main():

#     provider = PollinationsProvider()

#     await provider.connect()

#     try:

#         image_url = await provider.generate_image_url(
#             "futuristic AI dashboard"
#         )

#         image_bytes = await provider.generate_image(
#             "futuristic AI dashboard"
#         )

#         storage = AssetStorage()


#         image_path = await storage.save_image(
#             image_bytes,
#             "test.png"
#         )

#         video_bytes = await provider.generate_video(
#             "animate the dashboard ",
#             image_url
#         )

#         video_path = await storage.save_video(
#             video_bytes,
#             "test.mp4"
#         )

#         print(image_path)
#         print(video_path)

#     finally:
#         await provider.close()






# if __name__ == "__main__":
#     asyncio.run(main())