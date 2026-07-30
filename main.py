import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mcp_tools.asset_generation.providers.pollinations_provider import PollinationsProvider


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
GENERATED_ASSETS_DIR = PROJECT_ROOT / "assets"
GENERATED_SITE_DIST = PROJECT_ROOT / "generated_site" / "dist"
GENERATED_ASSETS_DIR.mkdir(exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateAssetRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32000)
    edit_request: str | None = Field(default=None, max_length=4000)
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)


def _safe_asset_id(asset_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", asset_id):
        raise HTTPException(status_code=422, detail="Asset ID may contain only letters, numbers, underscores, and hyphens.")
    return asset_id


def _asset_url(asset_id: str, extension: str) -> str:
    return f"/generated-assets/{asset_id}{extension}"


@app.post("/assets/{asset_id}/generate")
async def generate_asset(asset_id: str, request: GenerateAssetRequest):
    """Generate a standalone image for the manual Asset Studio."""
    asset_id = _safe_asset_id(asset_id)
    prompt = request.prompt.strip()
    if request.edit_request and request.edit_request.strip():
        prompt = f"{prompt}\n\nRequested adjustment: {request.edit_request.strip()}"

    provider = PollinationsProvider()
    try:
        image_bytes = await provider.generate_image(prompt, request.width, request.height)
    except Exception as exc:
        logger.exception("Image generation failed for asset %s", asset_id)
        raise HTTPException(status_code=502, detail="The image provider could not complete this generation. Please retry.") from exc

    file_path = GENERATED_ASSETS_DIR / f"{asset_id}.png"
    file_path.write_bytes(image_bytes)
    return {"asset_id": asset_id, "url": _asset_url(asset_id, ".png"), "revised_prompt": prompt}


@app.post("/assets/{asset_id}/edit")
async def edit_asset(asset_id: str, request: GenerateAssetRequest):
    """Edit a generated asset using Pollinations free img2img (?image=URL)."""
    asset_id = _safe_asset_id(asset_id)
    if not request.edit_request or not request.edit_request.strip():
        raise HTTPException(status_code=422, detail="edit_request is required for editing.")
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=422, detail="The original prompt is required.")

    # Build the public URL of the source image so Pollinations can fetch it for img2img
    source_url: str | None = None
    for ext in (".png", ".jpg", ".webp"):
        candidate = GENERATED_ASSETS_DIR / f"{asset_id}{ext}"
        if candidate.is_file():
            source_url = f"http://localhost:8000/generated-assets/{asset_id}{ext}"
            break

    provider = PollinationsProvider()
    try:
        edited_bytes = await provider.edit_image(
            original_prompt=request.prompt,
            edit_instruction=request.edit_request,
            width=request.width,
            height=request.height,
            source_image_url=source_url,
        )
    except Exception as exc:
        logger.exception("Image edit failed for asset %s", asset_id)
        raise HTTPException(status_code=502, detail="Image editing failed. Please retry.") from exc

    edited_id = f"{asset_id}_edited"
    file_path = GENERATED_ASSETS_DIR / f"{edited_id}.png"
    file_path.write_bytes(edited_bytes)
    return {"asset_id": edited_id, "url": _asset_url(edited_id, ".png"), "original_asset_id": asset_id}





@app.post("/assets/{asset_id}/upload")
async def upload_asset(asset_id: str, file: UploadFile = File(...)):
    """Upload a standalone image for the manual Asset Studio."""
    asset_id = _safe_asset_id(asset_id)
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file.")

    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(file.content_type, ".png")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    (GENERATED_ASSETS_DIR / f"{asset_id}{extension}").write_bytes(content)
    return {"asset_id": asset_id, "url": _asset_url(asset_id, extension)}


@app.get("/generated-preview/{full_path:path}")
def generated_preview(full_path: str):
    """Forward generated-site preview requests to the Vite preview server."""
    return RedirectResponse(f"http://localhost:5174/{full_path}")


app.mount("/generated-assets", StaticFiles(directory=GENERATED_ASSETS_DIR), name="generated-assets")

# Serve the React SPA — html=True enables SPA fallback (unknown paths return index.html)
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
