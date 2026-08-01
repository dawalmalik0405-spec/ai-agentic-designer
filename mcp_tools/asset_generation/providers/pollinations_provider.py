from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp

from mcp_tools.resilience import ProviderResilience


logger = logging.getLogger(__name__)


class PollinationsProvider:
    """Generate and edit images through Pollinations' free public HTTP endpoint."""

    def __init__(self, resilience: ProviderResilience | None = None):
        self.resilience = resilience or ProviderResilience.from_env("pollinations", logger=logger)

    async def connect(self) -> None:
        """No-op: the free HTTP API does not need a session."""

    async def close(self) -> None:
        """No-op: the free HTTP API does not need a session."""

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux",
    ) -> bytes:
        """Generate an image from a text prompt using the free Pollinations endpoint."""
        if not prompt.strip():
            raise ValueError("An image prompt is required.")

        # image.pollinations.ai - confirmed free, no API key required, supports ?model=
        url = f"https://image.pollinations.ai/prompt/{quote(prompt.strip(), safe='')}"
        params = {"model": model, "width": width, "height": height, "nologo": "true"}

        async def request_image() -> bytes:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status >= 400:
                        detail = (await response.text())[:500]
                        raise RuntimeError(f"Pollinations returned HTTP {response.status}: {detail}")
                    content_type = response.headers.get("content-type", "")
                    image_bytes = await response.read()
                    if not image_bytes or not content_type.startswith("image/"):
                        raise RuntimeError("Pollinations returned a response without image bytes.")
                    return image_bytes

        return await self.resilience.execute("generate_image", request_image)

    async def edit_image(
        self,
        original_prompt: str,
        edit_instruction: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux",
        source_image_url: str | None = None,
    ) -> bytes:
        """
        Edit an image using Pollinations' free img2img endpoint.
        If source_image_url is provided (a publicly accessible URL), passes ?image=URL
        for true image-to-image conditioning.
        Otherwise falls back to combining prompts and regenerating.
        """
        combined_prompt = f"{original_prompt.strip()}. {edit_instruction.strip()}"

        url = f"https://image.pollinations.ai/prompt/{quote(combined_prompt, safe='')}"
        params: dict = {"model": model, "width": width, "height": height, "nologo": "true"}
        if source_image_url:
            params["image"] = source_image_url

        async def request_edit() -> bytes:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status >= 400:
                        detail = (await response.text())[:500]
                        raise RuntimeError(f"Pollinations edit returned HTTP {response.status}: {detail}")
                    content_type = response.headers.get("content-type", "")
                    image_bytes = await response.read()
                    if not image_bytes or not content_type.startswith("image/"):
                        raise RuntimeError("Pollinations edit returned no image bytes.")
                    return image_bytes

        return await self.resilience.execute("edit_image", request_edit)








































# if __name__ == "__main__":
#     import asyncio

#     async def test():
#         print("Testing PollinationsProvider...")
#         provider = PollinationsProvider()
#         try:
#             # Step 1: Generate
#             prompt = "A cat in space, digital art"
#             print(f"\n1. Generating: '{prompt}'...")
#             image_bytes = await provider.generate_image(prompt, width=512, height=512, model="flux")
#             with open("test_generate_output.png", "wb") as f:
#                 f.write(image_bytes)
#             print(f"   Saved test_generate_output.png ({len(image_bytes):,} bytes)")

#             # Step 2: Edit with img2img (using a public URL of the saved image)
#             # For a real test, pass source_image_url to the edit method.
#             # Here we test the prompt-combination fallback:
#             edit_instruction = "Add a rocket ship flying past the cat"
#             print(f"\n2. Editing with instruction: '{edit_instruction}'...")
#             edited_bytes = await provider.edit_image(
#                 original_prompt=prompt,
#                 edit_instruction=edit_instruction,
#                 width=512,
#                 height=512,
#             )
#             with open("test_edit_output.png", "wb") as f:
#                 f.write(edited_bytes)
#             print(f"   Saved test_edit_output.png ({len(edited_bytes):,} bytes)")

#         except Exception as e:
#             print(f"Test failed: {e}")

#     asyncio.run(test())
