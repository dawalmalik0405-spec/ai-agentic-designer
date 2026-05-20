# Agentic AI UI Designer

`Agentic AI UI Designer` is a FastAPI + LangGraph system for turning a user prompt into a multi-page React website project.

The project is currently in a restart/simplification phase. The active implementation is intentionally small, while MCP tooling is kept in the repo for the next stage.

## Current Implementation

The live backend graph is:

```text
Prompt
  -> Planner Agent
  -> Code Agent
  -> Packaged React project
```

The frontend sends prompts to the backend, receives generated files, and renders them in an in-app preview plus code view.

### Active Agents

The live graph currently uses:

1. `planner`
2. `code`

The planner produces validated structured output for:

- `plan`
- `design`
- `pages`
- `ui`

The code agent consumes that state and returns a packaged Vite-style React project.

Review, repair, and research agents have been removed from the active code path during the restart. They can be reintroduced later if they are rebuilt around a smaller, tested workflow.

## MCP Status

MCP tooling is intentionally kept.

Current MCP entrypoint:

```text
mcp_tools/initialize_mcps.py
```

Configured MCP servers:

- Firecrawl
- Context7
- Filesystem
- Playwright

Current state:

- MCP manager code is present.
- `langchain-mcp-adapters` remains in `requirements.txt`.
- `agents/designing_agent.py` still uses `get_tools_for_agent`.
- MCP is not currently wired into the live LangGraph path.

Recommended next MCP step:

```text
Planner -> Design Context MCP Node -> Code
```

That keeps the system focused while allowing Context7 or filesystem-backed design context to improve generation quality.

## Current Packaged Output

The code agent emits a runnable Vite-style React project structure:

```text
package.json
index.html
vite.config.js
src/main.jsx
src/styles.css
src/App.jsx
src/pages/*.jsx
```

## Current Frontend

The frontend is a React + TypeScript app served by FastAPI.

It currently provides:

- prompt input
- style selector
- generation status messages
- file count and page count summary
- code tab with file list and file viewer
- preview tab using an iframe-based runtime

The preview renders generated React code inside an iframe `srcDoc` runtime.

## Active Project Structure

```text
ai_agentic_designer
|- agents
|  |- code_agent.py
|  |- designing_agent.py
|  |- graphs.py
|  |- llm.py
|  |- planner_agent.py
|  |- state.py
|  `- __init__.py
|- frontend
|  |- src
|  |  |- App.tsx
|  |  |- Components
|  |  |  |- ChatPanel.tsx
|  |  |  `- PreviewPanel.tsx
|  |  |- index.css
|  |  `- main.tsx
|  |- package.json
|  `- vite.config.ts
|- mcp_tools
|  `- initialize_mcps.py
|- node
|  |- nodes.py
|  `- __init__.py
|- main.py
|- requirements.txt
`- README.md
```

## Removed During Restart

These files are no longer part of the current workspace:

- `agents/research_agent.py`
- `agents/review_agent.py`
- `agents/repair_agent.py`
- old generated `design_tokens/*.json`
- old generated `page_templates/*.json`

## Supported Design Styles

The planner currently supports:

- `glassmorphism`
- `skeuomorphism`
- `claymorphism`
- `minimalism`
- `liquid_glass`
- `neo_brutalism`

## Models

The current implementation uses NVIDIA-hosted models through `langchain_nvidia_ai_endpoints`.

Current defaults are defined in `agents/llm.py`:

```env
PLANNING_MODEL=qwen/qwen3-next-80b-a3b-instruct
CODE_MODEL=qwen/qwen3-next-80b-a3b-instruct
```

The code model default was moved away from the older Qwen coder endpoint because that endpoint is no longer usable.

## Environment

Current backend environment variables:

```env
NVIDIA_API_KEY=...
PLANNING_MODEL=qwen/qwen3-next-80b-a3b-instruct
CODE_MODEL=qwen/qwen3-next-80b-a3b-instruct
LLM_MAX_RETRIES=2
LLM_RETRY_DELAY_SECONDS=2
PLANNING_TOP_P=0.95
CODE_TOP_P=0.95
PLANNING_MAX_TOKENS=16384
CODE_MAX_TOKENS=16384
PLANNING_REASONING=true
PLANNING_REASONING_EFFORT=high
PRINT_AGENT_JSON=false
LOG_LEVEL=INFO
MCP_FILESYSTEM_ROOT=...
FIRECRAWL_API_KEY=...
```

`FIRECRAWL_API_KEY` is only needed when Firecrawl MCP is used.

## Run The Project

From the project root:

```powershell
uvicorn main:app --reload
```

The frontend build is served by FastAPI from:

```text
frontend/dist
```

Rebuild the frontend after UI changes:

```powershell
cd frontend
npm.cmd run build
```

## Current Status

Implemented:

- FastAPI `/generate` endpoint
- LangGraph planner -> code pipeline
- required style selection
- validated planner JSON
- parallel page code generation
- packaged React/Vite output
- terminal progress logging
- frontend prompt UI
- iframe-based preview
- code tab file viewer
- MCP manager retained for future wiring

Not currently active:

- Research Agent
- Review Agent
- Repair Agent
- automatic browser review
- automatic repair loop
- image generation
- SSE streaming
- Monaco editor
- checkpointing
- LangSmith tracing
- rate limiting

## Recommended Next Build Order

1. Stabilize planner -> code generation.
2. Add a small MCP-backed design context node.
3. Add deterministic generated-file validation.
4. Add repair only after validation is reliable.
5. Add Playwright review after local preview/build output is stable.
6. Add streaming and frontend editor improvements.
