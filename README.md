# AI Agentic Designer

AI Agentic Designer is a local full-stack prototype for generating, previewing, extending, and asset-enhancing React websites with an agentic workflow. It combines a FastAPI backend, LangGraph orchestration, LLM-powered planning/code agents, a React control panel, generated Vite websites, and an Asset Studio for approving and injecting generated assets.

The system is designed around an iterative website-building workflow:

```text
Create project
  -> Generate page/site from prompt
  -> Preview website
  -> Generate assets
  -> Approve, regenerate, or delete assets
  -> Apply approved assets
  -> Restart/reuse preview
  -> Add more pages to the same project
```

## Current Capabilities

- Create and manage projects from the dashboard.
- Generate an initial website/page through a LangGraph pipeline.
- Stream generation progress into the Chat Panel.
- Start or reuse a generated-site Vite preview server.
- View generated code from the frontend.
- Generate page-specific assets into the local `assets/` directory.
- Review generated assets in Asset Studio.
- Select assets using approval toggles.
- Delete unwanted assets.
- Inject only approved assets into the generated React code.
- Add a new page to an existing project without regenerating the whole website.
- Connect added pages into the generated site's routing/navigation.

## Architecture

The repository has three main runtime surfaces:

```text
FastAPI backend
  Owns projects, database access, asset APIs, graph execution, static files, and preview server control.

React frontend
  Provides dashboard, chat workflow, workspace overview, preview panel, and asset studio.

Generated website
  A separate Vite React project written into generated_site/ and served on a preview port.
```

High-level data flow:

```text
frontend/
  -> FastAPI endpoints in main.py
    -> LangGraph graphs in agents/graphs.py
      -> node functions in node/nodes.py
        -> specialized agents in agents/
          -> structured Pydantic outputs in schema/
            -> generated_site/ and assets/
```

## Agent Graphs

### Initial Page/Site Graph

Defined in `agents/graphs.py` as the main `graph`.

```text
START
  -> architect
  -> research
  -> design
  -> page
  -> page_code
END
```

Purpose:

- `architect`: builds project structure, goals, page blueprints, and research requirements.
- `research`: gathers market/reference context for the requested site.
- `design`: creates the design system, visual rules, typography, spacing, motion patterns, and component guidance.
- `page`: creates page-level section/component plans.
- `page_code`: writes the React/Vite generated website into `generated_site/`.

### Asset Generation Graph

Defined as `asset_graph`.

```text
START
  -> asset_plan
  -> asset_gen
END
```

Purpose:

- Plans required visual assets from the current page/design/code outputs.
- Generates or resolves assets and stores them under `assets/`.
- Registers assets so the frontend can display them in Asset Studio.

### Asset Injection Graph

Defined as `asset_injection_graph`.

```text
START
  -> asset_injection
  -> dev_server
END
```

Purpose:

- Receives only assets marked `Approved`.
- Uses the asset injection agent to update generated React code.
- Converts asset references into backend-served absolute URLs.
- Starts or reuses the generated-site Vite preview server.

### Add Page Graph

Defined as `add_page_graph`.

```text
START
  -> architect
  -> research
  -> design
  -> page
  -> page_code
  -> route_update
  -> dev_server
END
```

Purpose:

- Adds a new page to the current project.
- Reuses the existing project context instead of creating a fresh website.
- Runs the full page-specific planning/design/code flow for that new page.
- Writes the page into `generated_site/src/pages/`.
- Updates generated-site routing and navigation.
- Starts or reuses the preview server.

## User Workflow

### 1. Create A Project

Use the dashboard to create a project. This creates a database record but does not generate the website yet.

### 2. Generate The First Page/Site

Open the Chat Panel, select a project, enter a prompt, choose a style, and click `Generate`.

The frontend calls:

```text
POST /api/projects/{project_id}/generate-page
GET  /api/projects/{project_id}/generate-page/stream
```

The streamed graph progress is shown in the Chat Panel.

### 3. Preview The Website

Open the project workspace and click `Preview Website`.

The frontend calls:

```text
POST /api/projects/{project_id}/build
GET  /api/projects/{project_id}/preview-status
GET  /api/projects/{project_id}/code
```

The generated site is served from `generated_site/` through a Vite dev server.

### 4. Generate Assets

From the Preview Panel, click `Generate Assets`.

The frontend calls:

```text
POST /api/projects/{project_id}/generate-assets
```

After generation, the UI redirects to Asset Studio.

### 5. Approve, Regenerate, Or Delete Assets

Asset Studio displays assets from the database and local registry/folder fallback.

Useful endpoints:

```text
GET    /api/projects/{project_id}/assets
PATCH  /api/projects/{project_id}/assets/{asset_id}/approval
DELETE /api/projects/{project_id}/assets/{asset_id}
POST   /api/projects/{project_id}/assets/upload
POST   /api/projects/{project_id}/assets/generate
```

Only assets whose status is `Approved` are used by the injection graph.

### 6. Apply Approved Assets

In Asset Studio, click `Apply Approved Assets`.

The frontend calls:

```text
POST /api/projects/{project_id}/inject-assets
```

The backend collects approved assets, converts their paths to browser-safe URLs, updates generated code, and returns the user to the preview flow.

### 7. Add A New Page

From a project workspace, click `Add Page`.

The UI redirects to Chat Panel in `Generate New Page` mode with the current project preselected. Enter a page name, a page prompt, select a style, and click `Generate New Page`.

The frontend calls:

```text
POST /api/projects/{project_id}/add-page
```

The backend runs the full add-page graph for that page and updates only the existing project.

## API Reference

### Projects

```text
GET  /api/projects
POST /api/projects?name={project_name}
```

### Generation

```text
POST /api/projects/{project_id}/generate
POST /api/projects/{project_id}/generate-page
GET  /api/projects/{project_id}/generate-page/stream
POST /api/projects/{project_id}/cancel
POST /api/projects/{project_id}/add-page
```

### Preview And Code

```text
POST /api/projects/{project_id}/build
GET  /api/projects/{project_id}/preview-status
GET  /api/projects/{project_id}/code
GET  /api/projects/{project_id}/design-output
```

### Assets

```text
GET    /api/projects/{project_id}/assets
POST   /api/projects/{project_id}/generate-assets
POST   /api/projects/{project_id}/inject-assets
PATCH  /api/projects/{project_id}/assets/{asset_id}/approval
DELETE /api/projects/{project_id}/assets/{asset_id}
POST   /api/projects/{project_id}/assets/upload
POST   /api/projects/{project_id}/assets/generate
```

### Static Files

```text
/generated-assets/*
```

Serves files from the local `assets/` directory.

## Repository Structure

```text
ai_agentic_designer/
|- agents/
|  |- architect_agent.py
|  |- asset_agent.py
|  |- asset_injection_agent.py
|  |- designing_agent.py
|  |- graphs.py
|  |- llm.py
|  |- page_agent.py
|  |- page_code_agent.py
|  `- research_agent.py
|- assets/
|  |- images/
|  `- registry.json
|- frontend/
|  |- src/
|  |  |- components/
|  |  |  |- AssetsStudio.tsx
|  |  |  |- ChatPanel.tsx
|  |  |  |- PreviewPanel.tsx
|  |  |  `- WorkspaceOverview.tsx
|  |  |- App.tsx
|  |  |- index.css
|  |  `- main.tsx
|  |- package.json
|  `- vite.config.ts
|- generated_site/
|  |- src/
|  |- package.json
|  `- vite.config.*
|- mcp_tools/
|  |- asset_generation/
|  |- initialize_mcps.py
|  `- servers.json
|- node/
|  `- nodes.py
|- schema/
|  |- add_page.py
|  |- architect.py
|  |- asset.py
|  |- asset_gen.py
|  |- asset_injection.py
|  |- code.py
|  |- desighn.py
|  |- page_d.py
|  |- research.py
|  `- state.py
|- main.py
|- pipeline_utils.py
|- requirements.txt
`- README.md
```

## Key Files

- `main.py`: FastAPI app, database models, project endpoints, asset endpoints, preview endpoints, frontend/static serving.
- `agents/graphs.py`: LangGraph graph definitions and graph runner helpers.
- `node/nodes.py`: graph node functions that connect graph state to concrete agents.
- `agents/llm.py`: LLM factory functions and model configuration.
- `agents/page_code_agent.py`: generated-site code writing, route updates, dependency install, and Vite dev server control.
- `agents/asset_injection_agent.py`: approved asset injection into generated code.
- `frontend/src/components/ChatPanel.tsx`: first-page and add-page prompt workflow.
- `frontend/src/components/AssetsStudio.tsx`: asset review, approval, deletion, and injection controls.
- `frontend/src/components/PreviewPanel.tsx`: generated site preview and code view.

## Requirements

Backend:

- Python 3.11+
- PostgreSQL
- NVIDIA API key for NVIDIA-hosted models
- Gemini API key for the asset injection model

Frontend:

- Node.js 20+
- npm

Python dependencies are listed in `requirements.txt`.

Frontend dependencies are listed in:

```text
frontend/package.json
generated_site/package.json
```

## Environment Variables

Create a `.env` file in the project root.

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_designer

NVIDIA_API_KEY=your_nvidia_key
GEMINI_API_KEY=your_gemini_key

PLANNING_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
REASON_MODEL=google/diffusiongemma-26b-a4b-it
RESEARCH_MODEL=llama-3.3-70b-versatile
CODE_MODEL=deepseek-ai/deepseek-v4-pro
GEMINI_MODEL=gemini-2.5-flash

NVIDIA_CODE_MAX_TOKENS=16384
LOG_LEVEL=INFO

BACKEND_PUBLIC_URL=http://localhost:8000
MCP_CONFIG_PATH=mcp_tools/servers.json
MCP_FILESYSTEM_ROOT=.
FIRECRAWL_API_KEY=optional_firecrawl_key
```

Notes:

- `DATABASE_URL` defaults to a local PostgreSQL URL in `main.py`, but setting it explicitly is recommended.
- `BACKEND_PUBLIC_URL` is used to convert generated asset paths into browser-safe absolute URLs.
- `FIRECRAWL_API_KEY` is only required when using Firecrawl-backed research tooling.

## Installation

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Frontend

```powershell
cd frontend
npm install
cd ..
```

### 3. Generated Site Dependencies

The generated-site dev server manager can install dependencies when needed, but you can also install them manually:

```powershell
cd generated_site
npm install
cd ..
```

## Running Locally

Start the backend:

```powershell
uvicorn main:app --reload
```

Start the frontend development server:

```powershell
cd frontend
npm run dev
```

Then open the frontend URL printed by Vite.

The generated website preview is managed separately from the app frontend. It is started through:

```text
POST /api/projects/{project_id}/build
```

or automatically after asset injection/add-page workflows. By default the generated site uses Vite on port `5173`.

## Build And Verification

Compile backend files:

```powershell
python -m py_compile main.py agents\graphs.py node\nodes.py agents\page_code_agent.py agents\asset_injection_agent.py
```

Build the frontend:

```powershell
cd frontend
npm run build
```

Run provider smoke checks if needed:

```powershell
python test_provider_smoke.py
```

## Asset Storage

Generated assets live under:

```text
assets/
assets/images/
assets/registry.json
```

The backend serves this folder at:

```text
/generated-assets/
```

For example:

```text
assets/images/home_hero.webp
```

is available in the browser as:

```text
http://localhost:8000/generated-assets/images/home_hero.webp
```

Asset injection uses absolute URLs so the generated Vite preview can load backend-served files correctly.

## Database

The backend currently defines two primary tables:

- `projects`
- `assets`

Tables are created through SQLAlchemy metadata at application startup.

Project records store:

- project id
- name
- page count
- status
- last updated timestamp
- graph output JSON

Asset records store:

- asset id
- project id
- name
- type
- purpose
- dimensions
- URL/path
- approval status

## Troubleshooting

### Add Page Fails At The `page` Node

If logs show:

```text
During task with name 'page'
TimeoutError
```

the add-page graph reached the Page Agent and timed out while asking the LLM to create the page plan. The route update and code injection nodes were not reached.

Useful checks:

- Reduce the page prompt size.
- Increase provider timeout/retry settings in the resilience layer.
- Confirm the configured model is reachable.
- Retry after the provider circuit closes.

### Port 5173 Is Already In Use

The generated-site dev server manager is designed to reuse an existing Vite server when possible. If the port is still blocked by a stale process, stop that process or change the preview port in the generated-site dev server logic.

### Assets Show In Asset Studio But Not In Preview

Check that:

- the asset file exists under `assets/images/`;
- the asset is marked `Approved`;
- `POST /api/projects/{project_id}/inject-assets` completed successfully;
- generated React code uses `http://localhost:8000/generated-assets/...`;
- the backend is running while the generated Vite preview is open.

### Frontend Changes Do Not Appear

If using the FastAPI-served production frontend, rebuild:

```powershell
cd frontend
npm run build
```

If using Vite dev mode, keep `npm run dev` running in `frontend/`.

## Development Notes

- The app frontend and generated website are separate React/Vite projects.
- The app frontend lives in `frontend/`.
- The generated website lives in `generated_site/`.
- The backend controls the generated-site preview server.
- Asset Studio approval is the gate for asset injection.
- Add Page is intentionally scoped to the existing project and should not regenerate a new site shell.
- MCP configuration is kept under `mcp_tools/` for research, design context, and future tool expansion.

## Current Roadmap

- Improve timeout handling and user-facing failure messages for graph nodes.
- Add progress streaming for Add Page and Asset Injection workflows.
- Add deterministic validation for generated files before starting preview.
- Add better route/nav patching safeguards for generated sites.
- Add per-page asset generation and injection controls.
- Add code diff view after asset injection and add-page runs.
- Add Playwright-based visual validation for generated previews.

## Status

This project is actively evolving. The current implementation supports the main project generation workflow, asset approval/injection workflow, and add-page workflow, but agent quality and provider reliability still depend on model availability, prompt size, and API latency.
