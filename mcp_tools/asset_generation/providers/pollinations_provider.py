from __future__ import annotations

import base64
import json
import logging
import aiohttp
import os

from mcp_tools.initialize_mcps import create_mcp_client
from mcp_tools.resilience import ProviderResilience

from ..storage.asset_storage import AssetStorage


logger = logging.getLogger(__name__)


class PollinationsProvider:

    def __init__(
        self,
        resilience: ProviderResilience | None = None
    ):

        self.client = create_mcp_client(
            allowed_servers=["pollinations"]
        )

        self.session = None
        self.resilience = (
            resilience
            or ProviderResilience.from_env(
                "pollinations",
                logger=logger
            )
        )

    async def connect(self):

        await self.client.create_all_sessions()

        self.session = self.client.get_session(
            "pollinations"
        )

    async def close(self):

        await self.client.close_all_sessions()


    def _decode_base64(
        self,
        value: str
    ) -> bytes:

        if "," in value and value.strip().startswith("data:"):
            value = value.split(
                ",",
                1
            )[1]

        return base64.b64decode(
            value
        )


    async def _fetch_url_bytes(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None
    ) -> bytes:

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers
            ) as response:
                if response.status >= 400:
                    response_text = await response.text()
                    raise ValueError(
                        f"Image URL returned status {response.status}: "
                        f"{response_text[:500]}"
                    )

                return await response.read()


    def _compact_prompt(
        self,
        prompt: str,
        max_length: int = 1800
    ) -> str:

        cleaned = " ".join(
            prompt.split()
        )

        if len(cleaned) <= max_length:
            return cleaned

        return cleaned[:max_length].rsplit(
            " ",
            1
        )[0]


    def _pollinations_headers(
        self
    ) -> dict[str, str]:

        api_key = os.getenv(
            "POLLINATIONS_API_KEY"
        )

        if not api_key:
            return {}

        return {
            "Authorization": f"Bearer {api_key}"
        }


    async def _extract_image_bytes(
        self,
        result
    ) -> bytes:

        content_shapes: list[str] = []

        for item in result.content:
            content_shapes.append(
                item.__class__.__name__
            )

            data = getattr(
                item,
                "data",
                None
            )
            if data:
                return self._decode_base64(
                    data
                )

            blob = getattr(
                item,
                "blob",
                None
            )
            if blob:
                return self._decode_base64(
                    blob
                )

            resource = getattr(
                item,
                "resource",
                None
            )
            resource_blob = getattr(
                resource,
                "blob",
                None
            )
            if resource_blob:
                return self._decode_base64(
                    resource_blob
                )

            text = getattr(
                item,
                "text",
                None
            )
            if text:
                try:
                    payload = json.loads(
                        text
                    )
                except json.JSONDecodeError:
                    payload = {}

                for key in (
                    "image",
                    "imageBase64",
                    "base64",
                    "data",
                    "blob",
                ):
                    value = payload.get(
                        key
                    )
                    if value:
                        return self._decode_base64(
                            value
                        )

                image_url = (
                    payload.get("imageUrl")
                    or payload.get("url")
                )
                if image_url:
                    return await self._fetch_url_bytes(
                        image_url
                    )

        logger.warning(
            "Pollinations image response contained no image bytes",
            extra={
                "content_shapes": content_shapes
            }
        )

        raise ValueError(
            "No image returned."
        )

    async def generate_image_url(
        self,
        prompt: str,
        *,
        width: int | None = None,
        height: int | None = None
    ) -> str:

        arguments = {
            "prompt": prompt,
            "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        }

        if width:
            arguments["width"] = width

        if height:
            arguments["height"] = height

        result = await self.resilience.execute(
            "generate_image_url",
            lambda: self.session.call_tool(
                "generateImageUrl",
                arguments
            )
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
        result = await self.resilience.execute(
            "generate_video",
            lambda: self.session.call_tool(
                "generateVideo",
                {
                    "prompt": prompt,
                    "model": os.getenv("POLLINATIONS_VIDEO_MODEL", "veo-1080p"),
                    "duration": duration,
                    "aspectRatio": aspect_ratio,
                    "image": image_url,
                }
            )
        )

        content_shapes: list[str] = []
        print(f"[VIDEO DEBUG] result.content has {len(result.content)} item(s)")
        for item in result.content:
            content_shapes.append(item.__class__.__name__)

            resource = getattr(item, "resource", None)
            resource_blob = getattr(resource, "blob", None)
            if resource_blob:
                return base64.b64decode(resource_blob)

            for value in (
                getattr(item, "data", None),
                getattr(item, "blob", None),
                resource_blob,
            ):
                if value:
                    return self._decode_base64(value)

            text = getattr(item, "text", None)
            if text:
                stripped = text.strip()
                
                # Detect explicit MCP failure
                if "aborted" in stripped.lower() or "operation was aborted" in stripped.lower():
                    raise ValueError(
                        "Pollinations video generation requires a POLLINATIONS_API_KEY. "
                        "Set it in your .env file to enable video generation. "
                        f"(MCP error: {stripped})"
                    )
                
                # Handle plain URL returned as raw text
                if stripped.startswith("http"):
                    return await self._fetch_url_bytes(
                        stripped,
                        headers=self._pollinations_headers(),
                    )

                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {}

                for key in ("videoBase64", "base64", "data", "blob"):
                    if payload.get(key):
                        return self._decode_base64(payload[key])

                returned_url = (
                    payload.get("videoUrl")
                    or payload.get("url")
                    or payload.get("video")
                    or payload.get("imageUrl")
                    or payload.get("image")
                )
                if returned_url and str(returned_url).startswith("http"):
                    return await self._fetch_url_bytes(
                        returned_url,
                        headers=self._pollinations_headers(),
                    )

        logger.error(
            "Pollinations MCP video response contained no usable media",
            extra={"content_shapes": content_shapes},
        )
        raise ValueError(
            "Pollinations MCP returned no video resource, base64 data, or video URL."
        )
    

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int | None = None,
        height: int | None = None
    ) -> bytes:
        try:
            image_url = await self.generate_image_url(
                prompt,
                width=width,
                height=height
            )
            return await self._fetch_url_bytes(
                image_url,
                headers=self._pollinations_headers()
            )
        except Exception as url_error:
            logger.warning(
                "Pollinations MCP image URL failed, trying binary image tool",
                extra={
                    "error_type": type(url_error).__name__,
                    "error": str(url_error)
                }
            )

        result = await self.resilience.execute(
            "generate_image",
            lambda: self.session.call_tool(
                "generateImage",
                {
                    "prompt": prompt,
                    "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
                    **({"width": width} if width else {}),
                    **({"height": height} if height else {}),
                }
            )
        )

        return await self._extract_image_bytes(
            result
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
