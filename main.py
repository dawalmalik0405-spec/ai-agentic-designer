from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv
import os

# Load .env with explicit path
env_path = os.path.join(os.path.dirname(__file__), ".env")
print("Looking for .env at:", os.path.abspath(env_path))
print("File exists:", os.path.exists(env_path))
load_dotenv(dotenv_path=env_path)
print("GROQ KEY:", os.getenv("GROQ_API_KEY"))



from ai_agentic_designer.agents.graphs import run_graph


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

@app.post("/generate")
def generate(request: PromptRequest):
    result = run_graph(request.prompt)
    return {"result": result}

# Serve React
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend/dist")
app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return FileResponse(f"{frontend_dist}/index.html")