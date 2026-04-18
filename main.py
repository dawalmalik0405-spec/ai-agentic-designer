from fastapi import FastAPI
from pydantic import BaseModel

from ai_agentic_designer.agents.graphs import create_agent_graph

app = FastAPI()
graph = create_agent_graph()


class PromptRequest(BaseModel):
    prompt: str


@app.get("/")
def root():
    return {"message": "Agentic UI Designer Running"}


@app.post("/generate")
def generate(request: PromptRequest):
    result = graph.invoke({"prompt": request.prompt}, config={"recursion_limit": 100})
    return {
        "site_spec": result.get("site_spec", {}),
        "figma_result": result.get("figma_result", {}),
    }
