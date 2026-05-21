import logging
import os
from typing import ClassVar

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

try:
    from .agents.graphs import run_graph
except ImportError:  # Support running `uvicorn main:app` from this directory.
    from agents.graphs import run_graph


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

project_root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
module_env = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=project_root_env)
load_dotenv(dotenv_path=module_env, override=False)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptRequest(BaseModel):
    VALID_STYLES: ClassVar[set[str]] = {
        "glassmorphism",
        "skeuomorphism",
        "claymorphism",
        "minimalism",
        "liquid_glass",
        "neo_brutalism",
    }

    prompt: str = Field(min_length=1, max_length=1000)
    selected_style: str = Field(min_length=1)

    @validator("prompt")
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Prompt must not be empty")
        return cleaned

    @validator("selected_style")
    def validate_selected_style(cls, value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
        if cleaned not in cls.VALID_STYLES:
            allowed = ", ".join(sorted(cls.VALID_STYLES))
            raise ValueError(f"selected_style must be one of: {allowed}")
        return cleaned


@app.post("/generate")
def generate(request: PromptRequest):
    try:
        result = run_graph(prompt=request.prompt, selected_style=request.selected_style)
        return {"result": result}
    except Exception as exc:
        logger.exception("Generation request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


frontend_dist = os.path.join(os.path.dirname(__file__), "frontend/dist")
assets_dir = os.path.join(frontend_dist, "assets")
generated_preview_root = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.getenv("GENERATED_PROJECT_DIR", ".generated/latest"),
        "dist",
    )
)

if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/generated-preview/{full_path:path}")
def generated_preview(full_path: str):
    if not os.path.isdir(generated_preview_root):
        raise HTTPException(status_code=404, detail="Generated preview build not found")

    requested_path = full_path.strip("/")
    candidate = os.path.abspath(os.path.join(generated_preview_root, requested_path))

    if not candidate.startswith(generated_preview_root):
        raise HTTPException(status_code=400, detail="Invalid preview path")

    if requested_path and os.path.isfile(candidate):
        return FileResponse(candidate)

    index_file = os.path.join(generated_preview_root, "index.html")
    if not os.path.isfile(index_file):
        raise HTTPException(status_code=404, detail="Generated preview index not found")

    return FileResponse(index_file)


@app.get("/{full_path:path}")
def catch_all(full_path: str):
    index_file = os.path.join(frontend_dist, "index.html")

    if not os.path.isfile(index_file):
        raise HTTPException(status_code=404, detail="Frontend build not found")

    return FileResponse(index_file)
