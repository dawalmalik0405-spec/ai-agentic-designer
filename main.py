import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime

# SQLAlchemy imports for Postgres
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
GENERATED_ASSETS_DIR = PROJECT_ROOT / "assets"

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

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

from fastapi.responses import StreamingResponse
import json

@app.get("/api/projects/{project_id}/generate/stream")
async def generate_project_stream(project_id: str, prompt: str, style: str, db: Session = Depends(get_db)):
    """SSE endpoint to stream real-time agent node execution updates from LangGraph"""
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_generator():
        # Cancel any active running task first
        if project_id in ACTIVE_TASKS:
            existing_task = ACTIVE_TASKS[project_id]
            if not existing_task.done():
                existing_task.cancel()
            ACTIVE_TASKS.pop(project_id, None)

        async def worker():
            from agents.graphs import run_graph_events
            try:
                # Stream nodes as they run
                async for event in run_graph_events(prompt=prompt, selected_style=style):
                    # event structure: {'node_name': { ... }}
                    for node_name in event.keys():
                        yield f"data: {json.dumps({'node': node_name, 'status': 'running'})}\n\n"
                        await asyncio.sleep(0.1)

                # Completed successfully
                with SessionLocal() as worker_db:
                    proj = worker_db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
                    if proj:
                        proj.status = "Completed"
                        proj.last_updated = datetime.utcnow()
                        worker_db.commit()
                yield f"data: {json.dumps({'node': 'complete', 'status': 'done'})}\n\n"

            except asyncio.CancelledError:
                with SessionLocal() as worker_db:
                    proj = worker_db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
                    if proj:
                        proj.status = "Cancelled"
                        worker_db.commit()
                yield f"data: {json.dumps({'node': 'cancelled', 'status': 'failed'})}\n\n"

            except Exception as e:
                logger.error(f"Error during graph execution: {e}")
                with SessionLocal() as worker_db:
                    proj = worker_db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
                    if proj:
                        proj.status = "Failed"
                        worker_db.commit()
                yield f"data: {json.dumps({'node': 'failed', 'error': str(e)})}\n\n"

        # Spawn task
        task = asyncio.create_task(
            asyncio.ensure_future(
                # wrap generator output
                worker()
            )
        )
        ACTIVE_TASKS[project_id] = task

        try:
            # Consume the worker's yielded strings
            async for chunk in worker():
                yield chunk
        finally:
            ACTIVE_TASKS.pop(project_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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

# Serve the generated website pages
GENERATED_SITE_DIR = PROJECT_ROOT / "generated_site"
if GENERATED_SITE_DIR.exists():
    app.mount("/generated-site", StaticFiles(directory=str(GENERATED_SITE_DIR)), name="generated-site")

@app.get("/api/projects/{project_id}/preview")
async def get_project_preview(project_id: str):
    """Serves the main entry point of the generated website"""
    index_path = GENERATED_SITE_DIR / "index.html"
    if not index_path.exists():
        # Fallback dummy page if website has not been generated yet
        return HTMLResponse(
            content="<html><body style='background:#07060d;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>No site preview available. Run generation first.</h2></body></html>", 
            status_code=200
        )
    return FileResponse(str(index_path))

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
