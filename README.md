# Agentic AI UI Designer

`Agentic AI UI Designer` is a FastAPI + LangGraph system for turning a user prompt into a multi-page React website project.

This repository has two important layers:

1. the current working implementation
2. the target production architecture

The current implementation is intentionally simpler than the target plan. This README tracks both.

## Current Implementation

Today, the live backend graph is:

```text
Prompt
  -> Planner Agent
  -> Code Agent
  -> Review Agent
  -> Repair Agent (conditional)
  -> Packaged React project
```

The frontend sends prompts to the backend, receives generated files, and renders them in an in-app preview plus code view.

### Current active agents

The live graph currently uses these agents:

1. `planner`
2. `code`
3. `review`
4. `repair`

The planner produces validated structured output for:

- `plan`
- `design`
- `pages`
- `ui`

The code agent consumes that state and returns a packaged Vite-style React project.

The review agent checks generated output for high-confidence issues.

The repair agent selectively rewrites files that failed review.

### Current packaged output

The code agent currently emits a runnable Vite-style project structure:

```text
package.json
index.html
vite.config.js
src/main.jsx
src/styles.css
src/App.jsx
src/pages/*.jsx
```

### Current frontend

The frontend is a React + TypeScript app served by FastAPI.

It currently provides:

- prompt input
- generation status messages
- file count and page count summary
- code tab with file list and file viewer
- preview tab using an iframe-based runtime

The preview no longer uses Sandpack. It renders generated React code inside an iframe `srcDoc` runtime.

## Target Vision

The target system is a multi-agent AI website generator that takes a user prompt and produces a complete premium multi-page React website with animations, 3D effects, smooth transitions, and style-specific design systems.

The target output is:

- premium visual quality
- consistent shared theme across all pages
- live preview inside the app
- editable code view
- real-time streaming progress
- automatic review and repair
- real component patterns grounded in external sources

## Target Stack

### Backend

- Python
- FastAPI
- LangGraph
- Groq
- Gemini
- Grok Imagine API

### MCP tools

- Firecrawl
- Context7
- Filesystem
- Playwright

### Frontend

- React
- TypeScript
- Tailwind CSS
- Monaco Editor
- iframe preview
- Server Sent Events

## Target Design Styles

The system is planned to support six premium styles. Each style should carry its own colors, motion language, surfaces, spacing, component rules, and visual effects.

### 1. Glassmorphism

- frosted glass
- blur
- transparency
- dark background
- neon accents

### 2. Skeuomorphism

- realistic textures
- strong depth shadows
- physical press effects

### 3. Claymorphism

- soft 3D clay forms
- pastel palettes
- spring-heavy motion

### 4. Minimalism

- maximum whitespace
- clean typography
- subtle fades only

### 5. Liquid Glass

- Vision Pro inspired translucency
- morphing blobs
- heavy blur and saturation

### 6. Neo Brutalism

- bold borders
- flat harsh shadows
- raw typography
- snap-like transitions

## Target Research Sources

The system is planned to use four external UI inspiration sources through a research layer.

### UIverse

- Tailwind and CSS components
- animated buttons
- cards
- copy-paste UI patterns

### ForgeUI

- animated React components
- Tailwind + Framer Motion patterns
- production-oriented UI structure

### UIlora

- dashboards
- loaders
- real product-style interface patterns

### Awwwards

- premium layouts
- color systems
- editorial and award-level composition patterns

## Target Agent Architecture

The production system is planned around eight agents.

### 1. Research Agent

- Tool: Firecrawl MCP
- Job: scrape UIverse, ForgeUI, UIlora, and Awwwards for relevant component patterns, palettes, motion ideas, and layout structures

### 2. Orchestrator Agent

- Tool: none
- Job: replace separate planning passes with one merged orchestration call that outputs pages, design system, page blueprints, and component strategy

### 3. Code Agent

- Tool: Context7 MCP
- Job: generate one React page at a time with accurate implementation details for GSAP, Framer Motion, Three.js, React Three Fiber, and related libraries

### 4. Image Agent

- Tool: Grok Imagine API
- Job: generate hero images, backgrounds, and illustration assets

### 5. Animation Agent

- Tool: none
- Job: apply style-specific motion systems and transitions

### 6. Integration Agent

- Tool: Filesystem MCP
- Job: wire pages into a complete project with shared layout, routing, theme files, transitions, and consistent structure

### 7. Review Agent

- Tool: Playwright MCP
- Job: run the site in a browser, navigate pages, screenshot sections, verify links and animations, and assign quality scores

### 8. Repair Agent

- Tool: none
- Job: fix only broken or low-scoring files and repeat up to a bounded retry limit

## Target Workflow

The planned parallel workflow is:

### Phase 1. Research

- Research Agent scrapes all research sources in parallel

### Phase 2. Planning

- Orchestrator Agent produces the full site specification in one call

### Phase 3. Generation

- Code Agent generates pages in parallel

### Phase 4. Polish

- Animation Agent and Image Agent run in parallel

### Phase 5. Integration

- Integration Agent assembles the project and saves files

### Phase 6. Review

- Review Agent validates the site in a browser and scores each page

### Phase 7. Repair

- Repair Agent fixes only low-scoring or broken pages, with bounded retries

## Target MCP Usage

### Context7 MCP

- connected to the Code Agent
- used to pull accurate docs for GSAP, ScrollTrigger, Three.js, React Three Fiber, Framer Motion, and Lenis

### Firecrawl MCP

- connected to the Research Agent
- used to scrape UIverse, ForgeUI, UIlora, and Awwwards

### Filesystem MCP

- connected to the Integration Agent
- used to save generated projects to disk in a structured React project layout

### Playwright MCP

- connected to the Review Agent
- used to open pages, navigate routes, capture screenshots, and verify runtime behavior

## Target Animation Stack

The planned animation stack includes:

- GSAP + ScrollTrigger
- Framer Motion
- React Three Fiber
- Lenis
- Splitting.js

Motion style should be matched to design style:

- Glassmorphism: smooth fluid transitions
- Neo Brutalism: sharp snap-like motion
- Claymorphism: spring-heavy animation
- Minimalism: subtle fade motion
- Liquid Glass: morphing fluid transitions
- Skeuomorphism: tactile press and release motion

## Target State Shape

The long-term `AgentState` should cover:

### Input

- `prompt`
- `selected_style`

### Research

- `inspiration`
- `component_patterns`

### Planning

- `plan`
- `design`
- `pages`

### Generation

- `current_page_index`
- `current_page_name`
- `generated_pages`
- `generated_images`

### Integration

- `files`
- `output_path`

### Review

- `page_scores`
- `page_issues`
- `repair_count`

### Streaming

- `current_agent`
- `current_phase`
- `progress_percentage`
- `is_complete`

## Target Frontend Layout

The planned frontend layout is:

```text
+------------------+--------------------------------+
|   Chat Panel     |         Preview Panel          |
|   30% width      |         70% width              |
|                  |                                |
|  Style selector  |  [Preview Tab] [Code Tab]     |
|  6 style buttons |                                |
|                  |  Preview: iframe runtime       |
|  Chat messages   |  Tailwind + animation libs     |
|  Agent updates   |                                |
|  SSE streaming   |  Code: file tree + Monaco      |
|                  |                                |
|  input + send    |  editable files + preview sync |
+------------------+--------------------------------+
```

### Chat panel goals

- style selector with six styles
- live agent updates
- chat history
- prompt input and send action

### Preview tab goals

- iframe runtime
- instant rendering
- Tailwind injected
- animation runtime support

### Code tab goals

- file tree
- Monaco editor
- click file to inspect and edit

## Target Streaming Flow

The target streaming model is SSE.

The frontend opens a streaming connection and receives events such as:

- `agent_start`
- `agent_done`
- `files`
- `error`
- `done`

This will replace the current wait-for-completion request flow.

## Production Features

The target production system should include:

- LangGraph checkpointing with SQLite
- LangGraph retry policies
- LangSmith tracing
- Pydantic input validation
- request rate limiting
- structured logging
- safe error handling and fallback behavior

## Build Order

### Week 1. Core backend

- merge planning into one Orchestrator Agent
- expand Code Agent to support six style systems
- add Context7 MCP
- keep parallel page generation
- test full pipeline end to end

### Week 2. MCP tools

- add Firecrawl + Research Agent
- add Filesystem + Integration Agent
- add Playwright + Review Agent
- add Grok Image Agent
- expand the repair loop

### Week 3. Production backend

- add SSE streaming endpoint
- add LangGraph checkpointing
- add error handling and logging everywhere
- add rate limiting and input validation
- add LangSmith tracing

### Week 4. Frontend

- add style selector
- connect the chat UI to SSE
- upgrade preview
- add Monaco editor and file tree
- polish the integrated experience

### Week 5. Deploy

- Docker setup
- deploy to Railway or Render
- add domain and SSL
- optimize performance

## Models

The current implementation uses NVIDIA-hosted models through `langchain_nvidia_ai_endpoints`.

Current defaults:

```env
PLANNING_MODEL=qwen/qwen3-next-80b-a3b-instruct
CODE_MODEL=qwen/qwen2.5-coder-32b-instruct
```

The target architecture may introduce additional provider-specific models for orchestration, code, images, and review.

## Environment

Current backend environment variables:

```env
NVIDIA_API_KEY=...
PLANNING_MODEL=qwen/qwen3-next-80b-a3b-instruct
CODE_MODEL=qwen/qwen2.5-coder-32b-instruct
LLM_MAX_RETRIES=2
LLM_RETRY_DELAY_SECONDS=2
PLANNING_TOP_P=0.95
CODE_TOP_P=0.95
PLANNING_MAX_TOKENS=16384
CODE_MAX_TOKENS=16384
PLANNING_REASONING=true
PLANNING_REASONING_EFFORT=high
PRINT_AGENT_JSON=true
LOG_LEVEL=INFO
```

## Run The Project

From the project root:

```powershell
uvicorn ai_agentic_designer.main:app --reload
```

The frontend build is served by FastAPI from:

```text
frontend/dist
```

Rebuild the frontend after UI changes:

```powershell
cd ai_agentic_designer/frontend
npm.cmd run build
```

## Project Structure

```text
ai_agentic_designer
|- agents
|  |- code_agent.py
|  |- design_agent.py
|  |- graphs.py
|  |- llm.py
|  |- page_agent.py
|  |- planner_agent.py
|  |- repair_agent.py
|  |- review_agent.py
|  |- state.py
|  `- ui_agent.py
|- docs
|- frontend
|  |- src
|  |  |- App.tsx
|  |  |- Components
|  |  |  |- ChatPanel.tsx
|  |  |  `- PreviewPanel.tsx
|  |  `- index.css
|  `- dist
|- mcp_server
|- node
|  `- nodes.py
|- main.py
`- requirements.txt
```

## Current Status

Implemented:

- LangGraph backend pipeline
- merged planner agent
- code generation agent
- conditional review and repair loop
- packaged React project output
- validated planner JSON
- parallel page generation
- terminal progress logging
- frontend prompt UI
- iframe-based preview
- code tab file viewer

Planned but not implemented:

- Research Agent
- Orchestrator Agent replacement
- Animation Agent
- Image Agent
- Integration Agent
- MCP tooling
- SSE streaming
- Monaco editor
- file tree editor
- checkpointing
- LangSmith tracing
- rate limiting
- deployment setup
