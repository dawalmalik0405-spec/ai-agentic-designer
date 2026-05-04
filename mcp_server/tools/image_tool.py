import hashlib
import os
from urllib.parse import quote

from langchain.tools import tool


DEFAULT_IMAGE_URL_TEMPLATE = (
    "https://image.pollinations.ai/prompt/{prompt}"
    "?width={width}&height={height}&seed={seed}&nologo=true&model=flux"
)


def _stable_seed(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def build_generated_image_url(
    prompt: str,
    *,
    width: int = 1536,
    height: int = 1024,
    seed_key: str = "",
) -> str:
    template = os.getenv("IMAGE_URL_TEMPLATE", DEFAULT_IMAGE_URL_TEMPLATE)
    seed = _stable_seed(seed_key or prompt)
    return template.format(
        prompt=quote(prompt, safe=""),
        width=width,
        height=height,
        seed=seed,
    )


@tool
def image_generation(prompt: str) -> str:
    """Return a generated remote image URL for the given prompt."""
    return build_generated_image_url(prompt)


