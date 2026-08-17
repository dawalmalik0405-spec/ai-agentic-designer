import asyncio
import sys
 
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


import logging
import os
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    HTMLResponse,
)
from agents.page_code_agent import PageCodeAgent, ProjectShellGenerator
from node.repair_nodes import run_repair_loop
import json
from pydantic import BaseModel
from datetime import datetime
from mcp_tools.asset_generation.providers.pollinations_provider import PollinationsProvider
from schema.page_d import PageDesignOutput
from schema.desighn import DesignSystemOutput
from schema.code import CodeGenerationOutput
from schema.asset_gen import GenerationStatus
from schema.asset_injection import ApprovedAsset
from schema.add_page import AddPageRequest

from agents.graphs import (
    run_graph_async,
    run_asset_graph_async,
    run_asset_injection_graph_async,
    run_add_page_graph_async,
)

# SQLAlchemy imports for Postgres
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
GENERATED_ASSETS_DIR = PROJECT_ROOT / "assets"


def _backend_public_url() -> str:
    return os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")


def _absolute_asset_url(url: str | None) -> str | None:
    if not url or url.startswith(("http://", "https://")):
        return url
    if url.startswith("/"):
        return f"{_backend_public_url()}{url}"
    return f"{_backend_public_url()}/{url}"


def _asset_public_reference(stored_path: str | None) -> tuple[str, bool, str | None]:
    """Return display name, local existence, and browser URL for an asset path."""
    if not stored_path:
        return "", False, None

    if stored_path.startswith(("http://", "https://")):
        return os.path.basename(stored_path), True, stored_path

    if stored_path.startswith("/generated-assets/"):
        stored_path = stored_path.removeprefix("/generated-assets/")

    raw_path = Path(stored_path)
    path_parts = raw_path.parts

    if raw_path.is_absolute():
        local_path = raw_path
        try:
            relative_path = local_path.resolve().relative_to(GENERATED_ASSETS_DIR.resolve())
        except ValueError:
            return raw_path.name, False, None
    else:
        if path_parts and path_parts[0] == GENERATED_ASSETS_DIR.name:
            relative_path = Path(*path_parts[1:])
        else:
            relative_path = raw_path

        local_path = GENERATED_ASSETS_DIR / relative_path
        if not local_path.exists() and len(relative_path.parts) == 1:
            image_relative_path = Path("images") / relative_path.name
            image_path = GENERATED_ASSETS_DIR / image_relative_path
            if image_path.exists():
                relative_path = image_relative_path
                local_path = image_path

    try:
        local_path.resolve().relative_to(GENERATED_ASSETS_DIR.resolve())
    except ValueError:
        return raw_path.name, False, None

    exists = local_path.exists()
    url = f"/generated-assets/{relative_path.as_posix()}" if exists else None
    return relative_path.name, exists, url


def _asset_local_path(stored_path: str | None) -> Path | None:
    if not stored_path or stored_path.startswith(("http://", "https://")):
        return None

    if stored_path.startswith("/generated-assets/"):
        stored_path = stored_path.removeprefix("/generated-assets/")

    raw_path = Path(stored_path)
    path_parts = raw_path.parts

    if raw_path.is_absolute():
        local_path = raw_path
    elif path_parts and path_parts[0] == GENERATED_ASSETS_DIR.name:
        local_path = PROJECT_ROOT / raw_path
    else:
        local_path = GENERATED_ASSETS_DIR / raw_path
        if not local_path.exists() and len(raw_path.parts) == 1:
            image_path = GENERATED_ASSETS_DIR / "images" / raw_path.name
            if image_path.exists():
                local_path = image_path

    try:
        resolved_path = local_path.resolve()
        resolved_path.relative_to(GENERATED_ASSETS_DIR.resolve())
    except ValueError:
        return None

    return resolved_path


def _asset_registry_entries() -> dict:
    registry_path = GENERATED_ASSETS_DIR / "registry.json"
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, "r", encoding="utf-8") as registry_file:
            registry_data = json.load(registry_file)
        return registry_data.get("assets", {})
    except Exception as e:
        logger.warning("Failed to read asset registry: %s", e)
        return {}


def _normalize_page_name(page_name: str | None) -> str | None:
    if not page_name:
        return None
    normalized = " ".join(page_name.strip().lower().split())
    return normalized or None


def _page_matches(candidate: str | None, target: str | None) -> bool:
    normalized_target = _normalize_page_name(target)
    if not normalized_target:
        return True
    normalized_candidate = _normalize_page_name(candidate)
    return normalized_candidate == normalized_target


def _project_pages_from_graph_output(graph_output: dict | None) -> list[dict]:
    if not graph_output:
        return []

    page_design = graph_output.get("page_design_output") or {}
    pages = page_design.get("pages") or []
    page_items = []
    for index, page in enumerate(pages):
        page_name = page.get("page_name") or f"Page {index + 1}"
        module_name = ProjectShellGenerator._module_name(page_name)
        route = ProjectShellGenerator._route_path(page_name, index)
        page_items.append({
            "page_name": page_name,
            "route": route,
            "file_path": f"src/pages/{module_name}.tsx",
            "module_name": module_name,
            "is_home": index == 0,
        })

    return page_items


def _display_name_from_module(module_name: str) -> str:
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", module_name).strip()
    return words or module_name


def _project_pages_from_generated_site(generated_site_dir: Path | None = None) -> list[dict]:
    site_dir = generated_site_dir or (PROJECT_ROOT / "generated_site")
    pages_dir = site_dir / "src" / "pages"
    if not pages_dir.exists():
        return []

    page_items = []
    tsx_files = sorted(pages_dir.glob("*.tsx"))
    tsx_files.sort(key=lambda item: 0 if item.stem.lower() in {"home", "homepage", "index"} else 1)

    for index, page_file in enumerate(tsx_files):
        module_name = page_file.stem
        if module_name.lower() in {"home", "homepage", "index"}:
            page_name = "Home"
            route = "/"
            is_home = True
        else:
            page_name = _display_name_from_module(module_name)
            route = ProjectShellGenerator._route_path(page_name, index)
            is_home = False

        page_items.append({
            "page_name": page_name,
            "route": route,
            "file_path": page_file.relative_to(site_dir).as_posix(),
            "module_name": module_name,
            "is_home": is_home,
        })

    return page_items


def _merge_project_pages(*page_groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen_keys: set[str] = set()
    for pages in page_groups:
        for page in pages:
            key = (page.get("route") or page.get("file_path") or page.get("page_name") or "").lower()
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            merged.append(page)
    return merged


def _project_pages(graph_output: dict | None) -> list[dict]:
    return _merge_project_pages(
        _project_pages_from_graph_output(graph_output),
        _project_pages_from_generated_site(),
    )


def _find_project_page(graph_output: dict | None, page_name: str | None) -> dict | None:
    pages = _project_pages(graph_output)
    if not pages:
        return None
    if not page_name:
        return pages[0]
    normalized = _normalize_page_name(page_name)
    return next((
        page for page in pages
        if _page_matches(page["page_name"], page_name)
        or _normalize_page_name(page.get("module_name")) == normalized
        or _normalize_page_name(page.get("route", "").strip("/").replace("-", " ")) == normalized
    ), None)


def _preview_url_for_page(route: str | None = None) -> str:
    base = "http://localhost:5173/site-preview/"
    if not route or route == "/":
        return base
    return f"{base}{route.lstrip('/')}"


def _approved_assets_for_project(project_id: str, db, page_name: str | None = None) -> list[ApprovedAsset]:
    registry_entries = _asset_registry_entries()
    db_assets = db.query(AssetDB).filter(
        AssetDB.project_id == project_id,
        AssetDB.status == "Approved"
    ).all()

    approved_assets = []
    for asset in db_assets:
        display_name, has_file, public_url = _asset_public_reference(asset.url or asset.name)
        if not has_file or not public_url:
            continue

        registry_entry = registry_entries.get(asset.id, {})
        asset_page_name = asset.page_name or registry_entry.get("page_name")
        if page_name and not _page_matches(asset_page_name, page_name):
            continue

        approved_assets.append(
            ApprovedAsset(
                asset_id=asset.id,
                name=display_name or asset.name,
                asset_type=asset.type,
                purpose=asset.purpose or registry_entry.get("purpose", ""),
                url=_absolute_asset_url(public_url) or public_url,
                page_name=asset_page_name,
                section_name=registry_entry.get("section_name"),
                dimensions=asset.dimensions,
            )
        )

    return approved_assets

app = FastAPI(title="AI Agentic Designer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep track of active generation tasks in-memory
import asyncio
ACTIVE_TASKS: dict[str, asyncio.Task] = {}

# --- Postgres Database Setup ---
# Default to a local postgres DB (make sure to set this in your .env)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Admin@localhost:5432/ai_designer")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProjectDB(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    pages = Column(Integer, default=0)
    status = Column(String, default="In Progress")
    last_updated = Column(DateTime, default=datetime.utcnow)
    graph_output = Column(JSON, nullable=True)

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class AssetDB(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    page_name = Column(String, nullable=True, index=True)
    name = Column(String)
    type = Column(String)
    purpose = Column(String)
    dimensions = Column(String)
    status = Column(String, default="Pending")
    url = Column(String, nullable=True)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

try:
    inspector = inspect(engine)
    if "assets" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("assets")}
        if "page_name" not in existing_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE assets ADD COLUMN page_name VARCHAR"))
except Exception as exc:
    logger.warning("Could not verify or add assets.page_name column automatically: %s", exc)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()





#page generation___
class PageGenerationRequest(BaseModel):
    prompt: str
    selected_style: str = "minimalism"


class AssetGenerationRequest(BaseModel):
    page_design_output: PageDesignOutput
    design_system_output: DesignSystemOutput
    page_code_output: CodeGenerationOutput


class AssetApprovalRequest(BaseModel):
    approved: bool






# Pydantic schema for API response
class ProjectResponse(BaseModel):
    id: str
    name: str
    pages: int
    status: str
    last_updated: datetime

    class Config:
        from_attributes = True

class GenerationRequest(BaseModel):
    prompt: str
    selected_style: str = "minimalism"

# --- API Endpoints ---
@app.get("/api/projects", response_model=dict)
def get_projects(db: Session = Depends(get_db)):
    """Returns the list of active projects from Postgres"""
    projects = db.query(ProjectDB).all()
    return {"projects": [ProjectResponse.model_validate(p).model_dump() for p in projects]}

@app.post("/api/projects", response_model=ProjectResponse)
def create_project(name: str, db: Session = Depends(get_db)):
    """Create a new project in Postgres"""
    import uuid
    new_proj = ProjectDB(
        id=f"proj_{uuid.uuid4().hex[:8]}",
        name=name,
        pages=0,
        status="In Progress",
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)
    return ProjectResponse.model_validate(new_proj)


@app.get("/api/projects/{project_id}/pages")
async def get_project_pages(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project_id": project_id,
        "pages": _project_pages(project.graph_output),
    }

@app.post("/api/projects/{project_id}/generate", response_model=ProjectResponse)
async def generate_project(project_id: str, request: GenerationRequest, db: Session = Depends(get_db)):
    """Triggers the LangGraph agent pipeline setup, returning 200 immediately to init SSE stream"""
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "Generating"
    project.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)



@app.post("/api/projects/{project_id}/cancel", response_model=ProjectResponse)
async def cancel_project_generation(project_id: str, db: Session = Depends(get_db)):
    """Manually stops an active generation stream in progress"""
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_id in ACTIVE_TASKS:
        task = ACTIVE_TASKS[project_id]
        if not task.done():
            task.cancel()
        ACTIVE_TASKS.pop(project_id, None)

    project.status = "Cancelled"
    project.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)

# --- Serve Static Files (Frontend & Assets) ---
if GENERATED_ASSETS_DIR.exists():
    app.mount("/generated-assets", StaticFiles(directory=str(GENERATED_ASSETS_DIR)), name="generated-assets")

# Serve the generated website pages (compiled dist output)
GENERATED_SITE_DIR = PROJECT_ROOT / "generated_site"



  # adjust import path to wherever it actually lives

@app.post("/api/projects/{project_id}/build")
async def start_dev_server(
    project_id: str,
    page_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Starts (or restarts) the Vite dev server for the generated site and streams progress."""
    if not GENERATED_SITE_DIR.exists():
        raise HTTPException(status_code=404, detail="No generated site found. Run generation first.")

    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_page = None
    if page_name:
        target_page = _find_project_page(project.graph_output, page_name)
        if not target_page:
            raise HTTPException(status_code=404, detail="Page not found in this project")

    page_design_output = None
    design_system_output = None
    if project.graph_output:
        stored = project.graph_output
        if stored.get("page_design_output"):
            page_design_output = PageDesignOutput(**stored["page_design_output"])
        if stored.get("design_system_output"):
            design_system_output = DesignSystemOutput(**stored["design_system_output"])

    agent = PageCodeAgent()

    async def run():
        repair_result = None

        if page_design_output:
            progress_queue: asyncio.Queue = asyncio.Queue()

            async def on_progress(step: str, status: str, msg: str, attempt: int | None = None):
                await progress_queue.put({
                    "step": step,
                    "status": status,
                    "msg": msg,
                    "attempt": attempt,
                })

            async def repair_worker():
                result = await run_repair_loop(
                    generated_site_dir=str(GENERATED_SITE_DIR),
                    page_design_output=page_design_output,
                    design_system_output=design_system_output,
                    selected_style="default",
                    on_progress=on_progress,
                )
                await progress_queue.put({"_done": True, "result": result})

            worker = asyncio.create_task(repair_worker())

            while True:
                event = await progress_queue.get()
                if event.get("_done"):
                    repair_result = event["result"]
                    break
                yield f"data: {json.dumps(event)}\n\n"

            await worker

            if repair_result and not repair_result.success:
                error_msg = "Build repair failed.\n\n" + "\n".join(repair_result.log_tail)
                yield f"data: {json.dumps({'step': 'build_check', 'status': 'error', 'msg': error_msg, 'attempt': repair_result.repair_attempts})}\n\n"
                return

        yield f"data: {json.dumps({'step': 'dev_server', 'status': 'running', 'msg': 'Installing dependencies and starting dev server...'})}\n\n"
        result = await agent.install_and_start_dev_server()

        if result["build_status"] != "Success":
            yield f"data: {json.dumps({'step': 'dev_server', 'status': 'error', 'msg': result['build_status'] + chr(10) + chr(10).join(result.get('log_tail', []))})}\n\n"
            return

        preview_url = _preview_url_for_page(target_page["route"] if target_page else None)
        yield f"data: {json.dumps({'step': 'complete', 'status': 'done', 'preview_url': preview_url})}\n\n"

    return StreamingResponse(run(), media_type="text/event-stream")





@app.get("/api/projects/{project_id}/preview-status")
async def preview_status(project_id: str, page_name: str | None = Query(default=None), db: Session = Depends(get_db)):
    agent = PageCodeAgent()
    status = agent.get_dev_server_status()
    if status.get("running") and page_name:
        project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
        if project:
            page = _find_project_page(project.graph_output, page_name)
            if page:
                status["preview_url"] = _preview_url_for_page(page["route"])
    return status






@app.get("/api/projects/{project_id}/code")
async def get_project_code(project_id: str):
    """Reads and returns the generated code files for the IDE panel"""
    code_files = {}
    
    # Common code file extensions to read
    allowed_extensions = {".html", ".css", ".js", ".ts", ".tsx", ".json"}
    
    if GENERATED_SITE_DIR.exists():
        for root, _, files in os.walk(GENERATED_SITE_DIR):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in allowed_extensions:
                    relative_path = file_path.relative_to(GENERATED_SITE_DIR).as_posix()
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            code_files[relative_path] = f.read()
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")
                        
    return {"files": code_files}

from fastapi import File, UploadFile
import shutil

@app.get("/api/projects/{project_id}/assets")
async def get_project_assets(
    project_id: str,
    page_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Retrieves the real database assets generated dynamically for this project"""
    db_assets = db.query(AssetDB).filter(AssetDB.project_id == project_id).all()
    registry_entries = _asset_registry_entries()
    
    # Return formatted schema payload
    assets_list = []
    seen_asset_ids = set()
    for asset in db_assets:
        registry_entry = registry_entries.get(asset.id, {})
        asset_page_name = asset.page_name or registry_entry.get("page_name")
        if page_name and not _page_matches(asset_page_name, page_name):
            continue

        display_name, has_file, public_url = _asset_public_reference(asset.url or asset.name)
        seen_asset_ids.add(asset.id)
        assets_list.append({
            "id": asset.id,
            "name": display_name or asset.name,
            "page_name": asset_page_name,
            "type": asset.type,
            "purpose": asset.purpose,
            "dimensions": asset.dimensions,
            "status": asset.status if has_file else "Pending",
            "url": public_url
        })

    # Backfill from the asset registry so already-generated files appear even
    # if the database rows were not created for this project.
    registry_path = GENERATED_ASSETS_DIR / "registry.json"
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as registry_file:
                registry_data = json.load(registry_file)

            for asset_id, entry in registry_data.get("assets", {}).items():
                if asset_id in seen_asset_ids:
                    continue
                if page_name and not _page_matches(entry.get("page_name"), page_name):
                    continue

                display_name, has_file, public_url = _asset_public_reference(
                    entry.get("file_path") or entry.get("source_url")
                )
                dimensions = f"{entry.get('width', '')} x {entry.get('height', '')}".strip()
                assets_list.append({
                    "id": asset_id,
                    "name": display_name or asset_id,
                    "page_name": entry.get("page_name"),
                    "type": entry.get("asset_type", "image"),
                    "purpose": entry.get("purpose", ""),
                    "dimensions": dimensions,
                    "status": "Pending",
                    "url": public_url,
                })
        except Exception as e:
            logger.warning("Failed to read asset registry: %s", e)

    return {"assets": assets_list}

@app.patch("/api/projects/{project_id}/assets/{asset_id}/approval")
async def set_asset_approval(
    project_id: str,
    asset_id: str,
    request: AssetApprovalRequest,
    db: Session = Depends(get_db)
):
    """Marks an asset as selected for injection or returns it to pending."""
    db_asset = db.query(AssetDB).filter(
        AssetDB.project_id == project_id,
        AssetDB.id == asset_id
    ).first()

    if not db_asset:
        registry_entry = _asset_registry_entries().get(asset_id)
        if not registry_entry:
            raise HTTPException(status_code=404, detail="Asset not found")

        display_name, has_file, public_url = _asset_public_reference(
            registry_entry.get("file_path") or registry_entry.get("source_url")
        )
        if not has_file or not public_url:
            raise HTTPException(status_code=400, detail="Asset file is not available")

        db_asset = AssetDB(
            id=asset_id,
            project_id=project_id,
            page_name=registry_entry.get("page_name"),
            name=public_url.removeprefix("/generated-assets/"),
            type=registry_entry.get("asset_type", "image"),
            purpose=registry_entry.get("purpose", ""),
            dimensions=f"{registry_entry.get('width', '')} x {registry_entry.get('height', '')}".strip(),
            status="Pending",
            url=public_url,
        )
        db.add(db_asset)

    db_asset.status = "Approved" if request.approved else "Pending"
    db.commit()
    db.refresh(db_asset)

    display_name, has_file, public_url = _asset_public_reference(db_asset.url or db_asset.name)
    return {
        "id": db_asset.id,
        "name": display_name or db_asset.name,
        "page_name": db_asset.page_name,
        "type": db_asset.type,
        "purpose": db_asset.purpose,
        "dimensions": db_asset.dimensions,
        "status": db_asset.status if has_file else "Pending",
        "url": public_url,
    }

@app.delete("/api/projects/{project_id}/assets/{asset_id}")
async def delete_project_asset(project_id: str, asset_id: str, db: Session = Depends(get_db)):
    """Deletes an asset record and its local generated file when one exists."""
    db_asset = db.query(AssetDB).filter(
        AssetDB.project_id == project_id,
        AssetDB.id == asset_id
    ).first()

    paths_to_delete: list[Path] = []
    deleted_registry = False

    if db_asset:
        for stored_path in (db_asset.url, db_asset.name):
            local_path = _asset_local_path(stored_path)
            if local_path and local_path.exists():
                paths_to_delete.append(local_path)

    registry_path = GENERATED_ASSETS_DIR / "registry.json"
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as registry_file:
                registry_data = json.load(registry_file)

            registry_assets = registry_data.get("assets", {})
            registry_entry = registry_assets.pop(asset_id, None)
            if registry_entry:
                deleted_registry = True
                local_path = _asset_local_path(registry_entry.get("file_path"))
                if local_path and local_path.exists():
                    paths_to_delete.append(local_path)

                with open(registry_path, "w", encoding="utf-8") as registry_file:
                    json.dump(registry_data, registry_file, indent=2)
        except Exception as e:
            logger.warning("Failed to update asset registry during delete: %s", e)

    deleted_files = []
    for local_path in dict.fromkeys(paths_to_delete):
        try:
            local_path.unlink()
            deleted_files.append(str(local_path.relative_to(PROJECT_ROOT)))
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("Failed to delete asset file %s: %s", local_path, e)

    if db_asset:
        db.delete(db_asset)
        db.commit()
    elif not deleted_registry and not deleted_files:
        raise HTTPException(status_code=404, detail="Asset not found")

    return {
        "status": "Success",
        "asset_id": asset_id,
        "deleted_files": deleted_files,
        "deleted_registry": deleted_registry,
    }

@app.post("/api/projects/{project_id}/assets/upload")
async def upload_project_asset(
    project_id: str,
    asset_id: str,
    page_name: str | None = Query(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Handles manual file uploads, updating database row status to Approved"""
    db_asset = db.query(AssetDB).filter(AssetDB.project_id == project_id, AssetDB.id == asset_id).first()
    if not db_asset:
        # Auto-create requirement row dynamically if it didn't exist in DB yet
        db_asset = AssetDB(
            id=asset_id,
            project_id=project_id,
            page_name=page_name,
            name=f"{asset_id}.png",
            type="image",
            purpose="Manually uploaded asset"
        )
        db.add(db_asset)
    elif page_name:
        db_asset.page_name = page_name

    if not GENERATED_ASSETS_DIR.exists():
        GENERATED_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename).suffix or ".png"
    target_filename = f"{asset_id}{extension}"
    target_path = GENERATED_ASSETS_DIR / target_filename

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update dynamic postgres record details
        db_asset.name = target_filename
        db_asset.status = "Pending"
        db_asset.url = f"/generated-assets/{target_filename}"
        db_asset.dimensions = "Custom" # Default indicator for manual uploads
        db.commit()
        
        logger.info(f"Successfully uploaded asset {target_filename} for project {project_id}")
        return {"status": "Success", "filename": target_filename, "url": db_asset.url}
    except Exception as e:
        logger.error(f"Failed to upload asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AssetGraphRequest(BaseModel):
    asset_id: str
    prompt: str
    width: int = 1024
    height: int = 1024
    page_name: str | None = None

@app.post("/api/projects/{project_id}/assets/generate")
async def generate_single_asset(project_id: str, request: AssetGraphRequest, db: Session = Depends(get_db)):
    """Manually generates a specific asset using the Pollinations AI Image Provider"""
    db_asset = db.query(AssetDB).filter(AssetDB.project_id == project_id, AssetDB.id == request.asset_id).first()
    
    # If the user is creating a brand-new asset from scratch
    if not db_asset:
        db_asset = AssetDB(
            id=request.asset_id,
            project_id=project_id,
            page_name=request.page_name,
            name=f"{request.asset_id}.png",
            type="image",
            purpose=f"AI Generated: {request.prompt}",
            dimensions=f"{request.width} x {request.height}"
        )
        db.add(db_asset)
    elif request.page_name:
        db_asset.page_name = request.page_name

    if not GENERATED_ASSETS_DIR.exists():
        GENERATED_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    target_filename = f"{request.asset_id}.png"
    target_path = GENERATED_ASSETS_DIR / target_filename

    try:
        # Instantiate Pollinations image generation provider (already imported in main.py)
        provider = PollinationsProvider()
        
        logger.info(f"Generating custom asset image: {request.prompt} ({request.width}x{request.height})")
        # Generate the asset via Pollinations endpoint
        image_bytes = await provider.generate_image(
            prompt=request.prompt,
            width=request.width,
            height=request.height
        )

        with open(target_path, "wb") as f:
            f.write(image_bytes)

        # Update database record details
        db_asset.status = "Pending"
        db_asset.name = target_filename
        db_asset.url = f"/generated-assets/{target_filename}"
        db_asset.dimensions = f"{request.width} x {request.height}"
        db_asset.purpose = f"AI Generated: {request.prompt}"
        db.commit()

        logger.info(f"Successfully generated asset {target_filename} for project {project_id}")
        return {"status": "Success", "filename": target_filename, "url": db_asset.url}
    except Exception as e:
        logger.error(f"Asset generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/generate-page")
async def generate_page(
    project_id: str,
    request: PageGenerationRequest,
    db: Session = Depends(get_db),
):

    project = (
        db.query(ProjectDB)
        .filter(ProjectDB.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    project.status = "Generating"
    db.commit()

    result = await run_graph_async(
        prompt=request.prompt,
        selected_style=request.selected_style,
    )

    serializable_result = {
        key: (value.model_dump() if hasattr(value, "model_dump") else value)
        for key, value in result.items()
    }

    project.graph_output = serializable_result
    project.status = "Failed" if result.get("build_success") is False else "Generated"
    project.pages = len(result["page_design_output"].pages) if result.get("page_design_output") else 0
    project.last_updated = datetime.utcnow()
    db.commit()

    if result.get("build_success") is False:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Project generated but build repair failed.",
                "repair_status": "failed",
                "repair_attempts": result.get("repair_attempts") or 0,
                "log_tail": result.get("log_tail") or [],
            },
        )

    return {
        "status": "success",
        "project_id": project.id,
        "graph_output": result,
        "repair_status": "success",
        "repair_attempts": result.get("repair_attempts") or 0,
        "repaired_files": result.get("repaired_files") or [],
    }



@app.get("/api/projects/{project_id}/design-output")
async def get_design_output(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project or not project.graph_output:
        raise HTTPException(status_code=404, detail="No design output found for this project.")
    return project.graph_output


@app.post("/api/projects/{project_id}/add-page")
async def add_project_page(
    project_id: str,
    request: AddPageRequest,
    db: Session = Depends(get_db),
):
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.graph_output:
        raise HTTPException(status_code=404, detail="Generate the project before adding pages.")

    stored = project.graph_output

    existing_architect_output = stored.get("architect_output")
    existing_research_output = stored.get("research_output")
    existing_design_system_output = stored.get("design_system_output")
    existing_page_design_output = stored.get("page_design_output")

    if not all([
        existing_architect_output,
        existing_research_output,
        existing_design_system_output,
        existing_page_design_output,
    ]):
        raise HTTPException(status_code=400, detail="Project graph output is incomplete.")

    from schema.architect import ArchitectOutput
    from schema.research import ResearchOutput

    architect_output = ArchitectOutput(**existing_architect_output)
    research_output = ResearchOutput(**existing_research_output)
    design_system_output = DesignSystemOutput(**existing_design_system_output)
    page_design_output = PageDesignOutput(**existing_page_design_output)

    existing_names = {
        _normalize_page_name(page["page_name"])
        for page in _project_pages(project.graph_output)
    }
    if _normalize_page_name(request.page_name) in existing_names:
        raise HTTPException(status_code=409, detail="A page with this name already exists.")

    result = await run_add_page_graph_async(
        project_id=project_id,
        page_name=request.page_name,
        prompt=request.prompt,
        selected_style=request.selected_style,
        existing_architect_output=architect_output,
        existing_research_output=research_output,
        existing_design_system_output=design_system_output,
        existing_page_design_output=page_design_output,
        generated_site_dir=str(GENERATED_SITE_DIR),
    )

    new_page_design_output = result.get("page_design_output")
    if not new_page_design_output or not new_page_design_output.pages:
        raise HTTPException(status_code=500, detail="Add page graph did not return a page design.")

    if result.get("build_success") is False:
        add_page_output = result.get("add_page_output")
        log_tail = result.get("log_tail") or []
        repair_attempts = result.get("repair_attempts") or 0
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Page code was generated but build repair failed.",
                "repair_status": "failed",
                "repair_attempts": repair_attempts,
                "log_tail": log_tail,
                "add_page_output": add_page_output.model_dump() if add_page_output else None,
            },
        )

    page_design_output.pages.append(new_page_design_output.pages[0])

    add_page_architect_output = result.get("architect_output")
    if add_page_architect_output and add_page_architect_output.page_blueprints:
        architect_output.page_blueprints.append(add_page_architect_output.page_blueprints[0])

    stored["architect_output"] = architect_output.model_dump()
    stored["page_design_output"] = page_design_output.model_dump()
    stored["last_add_page_output"] = {
        "architect_output": add_page_architect_output.model_dump() if add_page_architect_output else None,
        "research_output": result["research_output"].model_dump() if result.get("research_output") else None,
        "design_system_output": result["design_system_output"].model_dump() if result.get("design_system_output") else None,
        "page_design_output": new_page_design_output.model_dump(),
        "add_page_output": result["add_page_output"].model_dump() if result.get("add_page_output") else None,
    }

    project.graph_output = json.loads(json.dumps(stored))
    project.pages = len(page_design_output.pages)
    project.status = "Generated"
    project.last_updated = datetime.utcnow()
    db.commit()

    add_page_output = result.get("add_page_output")
    return {
        "status": "success",
        "project_id": project_id,
        "page_name": request.page_name,
        "repair_status": "success",
        "repair_attempts": result.get("repair_attempts") or 0,
        "repaired_files": result.get("repaired_files") or [],
        "log_tail": result.get("log_tail") or [],
        "add_page_output": add_page_output.model_dump() if hasattr(add_page_output, "model_dump") else add_page_output,
    }






@app.post("/api/projects/{project_id}/generate-assets")
async def generate_assets(
    project_id: str,
    page_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project or not project.graph_output:
        raise HTTPException(status_code=404, detail="No design output found. Generate the page first.")

    stored = project.graph_output

    page_design_output = PageDesignOutput(**stored["page_design_output"])
    target_page = None
    if page_name:
        target_page = next(
            (page for page in page_design_output.pages if _page_matches(page.page_name, page_name)),
            None,
        )
        if not target_page:
            raise HTTPException(status_code=404, detail="Page not found in this project")
        page_design_output = PageDesignOutput(
            global_rules=page_design_output.global_rules,
            pages=[target_page],
        )

    design_system_output = DesignSystemOutput(**stored["design_system_output"])
    page_code_output = CodeGenerationOutput(**stored["page_code_output"])

    result = await run_asset_graph_async(
        page_design_output=page_design_output,
        design_system_output=design_system_output,
        page_code_output=page_code_output,
    )

    logger.info("generated_asset_output: %s", result["generated_asset_output"])

    asset_output = result["asset_output"]
    generated_asset_output = result["generated_asset_output"]

    # Build a lookup of planned requirements (purpose, dimensions) by asset_id
    requirements_by_id = {req.asset_id: req for req in asset_output.assets}

    for gen_asset in generated_asset_output.assets:
        if gen_asset.status != GenerationStatus.SUCCESS:
            continue  # skip failed/skipped assets — nothing to register

        requirement = requirements_by_id.get(gen_asset.asset_id)
        asset_page_name = requirement.page_name if requirement else (target_page.page_name if target_page else None)
        existing = db.query(AssetDB).filter(
            AssetDB.project_id == project_id,
            AssetDB.id == gen_asset.asset_id
        ).first()

        display_name, has_file, public_url = _asset_public_reference(gen_asset.file_path)
        filename = display_name or f"{gen_asset.asset_id}.png"
        stored_name = public_url.removeprefix("/generated-assets/") if public_url else filename

        if existing:
            existing.status = "Pending"
            existing.page_name = asset_page_name
            existing.name = stored_name
            existing.type = gen_asset.asset_type.value
            existing.url = public_url
            existing.dimensions = f"{gen_asset.width} x {gen_asset.height}"
            existing.purpose = requirement.purpose if requirement else existing.purpose
        else:
            db.add(AssetDB(
                id=gen_asset.asset_id,
                project_id=project_id,
                page_name=asset_page_name,
                name=stored_name,
                type=gen_asset.asset_type.value,
                purpose=requirement.purpose if requirement else "",
                dimensions=f"{gen_asset.width} x {gen_asset.height}",
                status="Pending",
                url=public_url,
            ))

    db.commit()

    return {
        "status": "success",
        "project_id": project_id,
        "page_name": target_page.page_name if target_page else None,
        "asset_output": asset_output,
        "generated_asset_output": generated_asset_output,
    }


@app.post("/api/projects/{project_id}/inject-assets")
async def inject_approved_assets(
    project_id: str,
    page_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_page = _find_project_page(project.graph_output, page_name) if page_name else None
    if page_name and not target_page:
        raise HTTPException(status_code=404, detail="Page not found in this project")

    approved_assets = _approved_assets_for_project(project_id, db, page_name=page_name)
    if not approved_assets:
        raise HTTPException(status_code=400, detail="Select at least one approved asset before applying.")

    result = await run_asset_injection_graph_async(
        project_id=project_id,
        approved_assets=approved_assets,
        generated_site_dir=str(GENERATED_SITE_DIR),
        target_page_name=target_page["page_name"] if target_page else None,
    )

    injection_output = result.get("injection_output")
    return {
        "status": "success",
        "project_id": project_id,
        "page_name": target_page["page_name"] if target_page else None,
        "injection_output": injection_output.model_dump() if hasattr(injection_output, "model_dump") else injection_output,
        "dev_server_status": result.get("dev_server_status"),
        "preview_url": _preview_url_for_page(target_page["route"] if target_page else None),
        "log_tail": result.get("log_tail", []),
    }

    

from fastapi.responses import HTMLResponse

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_file = FRONTEND_DIST / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Frontend build not found. Run 'npm run build' inside frontend/")
        
        requested_file = FRONTEND_DIST / full_path
        if full_path and requested_file.is_file():
            return FileResponse(str(requested_file))
            
        return FileResponse(str(index_file))



















if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
