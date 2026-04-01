from fastapi import FastAPI
from pydantic import BaseModel

from mcp_server.tools.page_tools import generate_pages

app = FastAPI()


class ToolRequest(BaseModel):
    tool_name: str
    input: dict


# MCP Tool Registry
TOOLS = {
    "page_tool": generate_pages
}


@app.get("/")
def root():
    return {"message": "agentic designer tools server is running"}


@app.post("/run_tools")
def run_tools(request: ToolRequest):

    tool = TOOLS.get(request.tool_name)

    if not tool:
        return {"error": "Tool not found"}

    prompt = request.input.get("prompt")

    result = tool.invoke(prompt)

    return {
        "tool": request.tool_name,
        "result": result
    }