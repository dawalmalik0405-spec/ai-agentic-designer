import logging
import os
import hashlib
import json
import shutil
import subprocess
import time
import uuid
from typing import ClassVar, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from agents.asset_agent import AssetAgent
from mcp_tools.asset_generation.providers.pollinations_provider import PollinationsProvider


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


def load_graph_runners():
    try:
        from .agents.graphs import run_graph, run_graph_events
    except ImportError:  # Support running `uvicorn main:app` from this directory.
        from agents.graphs import run_graph, run_graph_events

    return run_graph, run_graph_events


def load_design_runners():
    try:
        from .agents.graphs import (
            plan_assets_async,
            run_approved_build_async,
            run_design_preview_async,
        )
    except ImportError:  # Support running `uvicorn main:app` from this directory.
        from agents.graphs import (
            plan_assets_async,
            run_approved_build_async,
            run_design_preview_async,
        )

    return run_design_preview_async, plan_assets_async, run_approved_build_async

PROJECT_ROOT = os.path.dirname(__file__)
GENERATED_SITE_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)
GENERATED_SITE_DIST = os.path.join(
    GENERATED_SITE_DIR,
    "dist"
)
FRONTEND_DIR = os.path.join(
    PROJECT_ROOT,
    "frontend"
)
FRONTEND_DIST = os.path.join(
    FRONTEND_DIR,
    "dist"
)

# Global tracker for the Vite Dev Server process
vite_dev_process = None
GENERATED_ASSETS_DIR = os.path.join(
    PROJECT_ROOT,
    "assets"
)
INSTALL_HASH_FILE = os.path.join(
    GENERATED_SITE_DIR,
    ".package-install.hash"
)


PROMPT_MAX_LENGTH = 60000


class PromptRequest(BaseModel):
    VALID_STYLES: ClassVar[set[str]] = {
        "glassmorphism",
        "skeuomorphism",
        "claymorphism",
        "minimalism",
        "liquid_glass",
        "neo_brutalism",
    }

    prompt: str = Field(min_length=1, max_length=PROMPT_MAX_LENGTH)
    selected_style: str = Field(min_length=1)

    @validator("prompt")
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Prompt must not be empty")
        return cleaned


class AssetSelectionRequest(BaseModel):
    asset_ids: list[str] = Field(default_factory=list)


class SectionEditRequest(BaseModel):
    page_name: str = Field(min_length=1)
    section_order: int = Field(ge=0)
    instruction: str = Field(min_length=3, max_length=4000)


class AssetEditRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    instruction: str = Field(min_length=3, max_length=4000)


class PageCodeRequest(BaseModel):
    page_name: str = Field(min_length=1)
    instruction: str | None = Field(default=None, max_length=4000)


class AddPageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=PROMPT_MAX_LENGTH)


# Drafts are deliberately in memory for the first implementation.  The direct
# /generate route remains untouched and sessions disappear when the API restarts.
design_sessions: dict[str, dict] = {}


def _api_value(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _api_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_api_value(item) for item in value]
    return value


def _session_payload(session_id: str, session: dict) -> dict:
    state = session["state"]
    return {
        "session_id": session_id,
        "status": session["status"],
        "prompt": state["user_prompt"],
        "selected_style": state["selected_style"],
        "wireframe": _api_value(state["page_design_output"]),
        "design_system": _api_value(state["design_system_output"]),
        "asset_options": _api_value(state.get("asset_output")),
        "generated_assets": _asset_candidates(state.get("generated_asset_output")),
        "selected_asset_ids": session.get("selected_asset_ids", []),
        "approved_pages": session.get("approved_pages", []),
    }


def _asset_candidates(generated_output) -> list[dict]:
    if generated_output is None:
        return []

    candidates = []
    for asset in generated_output.assets:
        if asset.status.value != "success" or not asset.file_path:
            continue
        relative_path = os.path.relpath(
            os.path.abspath(asset.file_path),
            GENERATED_ASSETS_DIR,
        ).replace(os.sep, "/")
        candidates.append({
            **asset.model_dump(mode="json"),
            "preview_url": f"/generated-assets/{relative_path}",
        })
    return candidates


def _get_design_session(session_id: str) -> dict:
    session = design_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Design session not found or API was restarted.")
    return session


    @validator("selected_style")
    def validate_selected_style(cls, value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
        if cleaned not in cls.VALID_STYLES:
            allowed = ", ".join(sorted(cls.VALID_STYLES))
            raise ValueError(f"selected_style must be one of: {allowed}")
        return cleaned


def _sse(
    payload: dict
) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def ensure_generated_site_entrypoints() -> None:
    os.makedirs(
        os.path.join(GENERATED_SITE_DIR, "src"),
        exist_ok=True
    )

    index_file = os.path.join(
        GENERATED_SITE_DIR,
        "index.html"
    )
    main_file = os.path.join(
        GENERATED_SITE_DIR,
        "src",
        "main.tsx"
    )

    if not os.path.isfile(index_file):
        with open(index_file, "w", encoding="utf-8") as file:
            file.write(
                """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Generated Website</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
            )

    vite_config = os.path.join(
        GENERATED_SITE_DIR,
        "vite.config.ts"
    )
    with open(vite_config, "w", encoding="utf-8") as file:
        file.write(
            """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
"""
        )

    postcss_config = os.path.join(
        GENERATED_SITE_DIR,
        "postcss.config.js"
    )
    with open(postcss_config, "w", encoding="utf-8") as file:
        file.write(
            """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""
        )

    tailwind_config = os.path.join(
        GENERATED_SITE_DIR,
        "tailwind.config.js"
    )
    with open(tailwind_config, "w", encoding="utf-8") as file:
        file.write(
            """/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "var(--primary)",
        secondary: "var(--secondary)",
        accent: "var(--accent)",
        dark_background: "var(--dark-background)",
        dark_surface: "var(--dark-surface)",
        success: "var(--success)",
      },
      borderRadius: {
        pill: "999px",
      },
      boxShadow: {
        medium: "0 18px 60px rgba(0, 0, 0, 0.28)",
      },
      fontFamily: {
        inter: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
"""
        )

    pages_dir = os.path.join(
        GENERATED_SITE_DIR,
        "src",
        "pages"
    )
    home_page_file = os.path.join(
        pages_dir,
        "HomePage.tsx"
    )
    main_needs_fallback = not os.path.isfile(main_file)

    if os.path.isfile(main_file):
        with open(main_file, "r", encoding="utf-8") as file:
            main_source = file.read()

        if (
            "./pages/HomePage" in main_source
            and not os.path.isfile(home_page_file)
        ):
            main_needs_fallback = True

    if main_needs_fallback:
        with open(main_file, "w", encoding="utf-8") as file:
            file.write(
                """import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

function App() {
  return (
    <main className="fallback-page">
      <section className="fallback-hero">
        <p className="fallback-eyebrow">Generated preview</p>
        <h1>Your generated site is ready to preview</h1>
        <p>
          The code agent did not create page modules for this run, so the backend
          created this safe preview shell instead of returning a 404.
        </p>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
            )

    index_css = os.path.join(
        GENERATED_SITE_DIR,
        "src",
        "index.css"
    )

    if not os.path.isfile(index_css):
        with open(index_css, "w", encoding="utf-8") as file:
            file.write(
                """:root {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #f8fafc;
  background: #07080b;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
}

.fallback-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  background:
    radial-gradient(circle at 20% 20%, rgba(211, 255, 114, 0.16), transparent 26rem),
    linear-gradient(135deg, #07080b, #14151b);
}

.fallback-hero {
  max-width: 760px;
}

.fallback-eyebrow {
  color: #d3ff72;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.16em;
}

.fallback-hero h1 {
  margin: 0;
  font-size: clamp(42px, 8vw, 86px);
  line-height: 0.95;
}

.fallback-hero p {
  color: #aeb6c2;
  font-size: 18px;
  line-height: 1.7;
}
"""
            )


def copy_generated_assets() -> None:
    if not os.path.isdir(GENERATED_ASSETS_DIR):
        return

    target = os.path.join(
        GENERATED_SITE_DIR,
        "public",
        "assets"
    )
    os.makedirs(
        os.path.dirname(target),
        exist_ok=True
    )
    shutil.copytree(
        GENERATED_ASSETS_DIR,
        target,
        dirs_exist_ok=True
    )


def generated_source_contains(
    text: str
) -> bool:
    src_dir = os.path.join(
        GENERATED_SITE_DIR,
        "src"
    )

    if not os.path.isdir(src_dir):
        return False

    for root, _, names in os.walk(src_dir):
        for name in names:
            if not name.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue

            path = os.path.join(root, name)

            try:
                with open(path, "r", encoding="utf-8") as file:
                    if text in file.read():
                        return True
            except UnicodeDecodeError:
                continue

    return False


def normalize_generated_package_json() -> None:
    package_json = os.path.join(
        GENERATED_SITE_DIR,
        "package.json"
    )

    if os.path.isfile(package_json):
        with open(package_json, "r", encoding="utf-8") as file:
            package_data = json.load(file)
    else:
        package_data = {
            "name": "generated-site",
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {},
            "dependencies": {},
            "devDependencies": {},
        }

    package_data.setdefault("private", True)
    package_data.setdefault("version", "0.0.0")
    package_data["type"] = "module"

    scripts = package_data.setdefault("scripts", {})
    scripts.setdefault("dev", "vite")
    scripts["build"] = "vite build"
    scripts.setdefault("preview", "vite preview")

    dependencies = package_data.setdefault("dependencies", {})
    dev_dependencies = package_data.setdefault("devDependencies", {})

    # GSAP and React Router v6 ship their own TypeScript definitions.
    # Generated package files sometimes hallucinate these @types packages,
    # and @types/gsap@^3.12.2 does not exist on npm.
    dependencies.pop("@types/gsap", None)
    dev_dependencies.pop("@types/gsap", None)
    dependencies.pop("@types/react-router-dom", None)
    dev_dependencies.pop("@types/react-router-dom", None)

    dependencies.setdefault("react", "^18.3.1")
    dependencies.setdefault("react-dom", "^18.3.1")

    if generated_source_contains("react-router-dom"):
        dependencies.setdefault("react-router-dom", "^6.28.0")

    if generated_source_contains("gsap"):
        dependencies.setdefault("gsap", "^3.12.5")

    if generated_source_contains("react-icons"):
        dependencies.setdefault("react-icons", "^5.2.1")

    if generated_source_contains("lucide-react"):
        dependencies.setdefault("lucide-react", "^0.395.0")

    if generated_source_contains("@heroicons/react"):
        dependencies.setdefault("@heroicons/react", "^2.1.3")

    dev_dependencies.setdefault("@vitejs/plugin-react", "^4.3.3")
    dev_dependencies.setdefault("vite", "^5.4.10")
    dev_dependencies.setdefault("typescript", "^5.6.2")
    dev_dependencies.setdefault("@types/react", "^18.3.12")
    dev_dependencies.setdefault("@types/react-dom", "^18.3.1")
    dev_dependencies.setdefault("tailwindcss", "^3.4.15")
    dev_dependencies.setdefault("postcss", "^8.4.49")
    dev_dependencies.setdefault("autoprefixer", "^10.4.20")

    with open(package_json, "w", encoding="utf-8") as file:
        json.dump(
            package_data,
            file,
            indent=2
        )
        file.write("\n")


def package_json_hash() -> str:
    package_json = os.path.join(
        GENERATED_SITE_DIR,
        "package.json"
    )

    if not os.path.isfile(package_json):
        return ""

    with open(package_json, "rb") as file:
        return hashlib.sha256(
            file.read()
        ).hexdigest()


def dependencies_need_install() -> bool:
    node_modules = os.path.join(
        GENERATED_SITE_DIR,
        "node_modules"
    )

    if not os.path.isdir(node_modules):
        return True

    current_hash = package_json_hash()

    if not current_hash:
        return False

    if not os.path.isfile(INSTALL_HASH_FILE):
        return True

    with open(INSTALL_HASH_FILE, "r", encoding="utf-8") as file:
        installed_hash = file.read().strip()

    return installed_hash != current_hash


def install_generated_site_dependencies() -> dict:
    package_json = os.path.join(
        GENERATED_SITE_DIR,
        "package.json"
    )

    if not os.path.isfile(package_json):
        return {
            "ok": True,
            "skipped": True,
            "stdout": "",
            "stderr": "No generated package.json found.",
            "returncode": 0,
        }

    if not dependencies_need_install():
        return {
            "ok": True,
            "skipped": True,
            "stdout": "Dependencies are already installed for current package.json.",
            "stderr": "",
            "returncode": 0,
        }

    result = subprocess.run(
        [
            "npm.cmd",
            "install",
        ],
        cwd=GENERATED_SITE_DIR,
        capture_output=True,
        text=True,
        timeout=240,
    )

    if result.returncode == 0:
        current_hash = package_json_hash()
        if current_hash:
            with open(INSTALL_HASH_FILE, "w", encoding="utf-8") as file:
                file.write(current_hash)

    return {
        "ok": result.returncode == 0,
        "skipped": False,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "returncode": result.returncode,
    }


def build_generated_site() -> dict:
    global vite_dev_process
    ensure_generated_site_entrypoints()
    copy_generated_assets()
    normalize_generated_package_json()

    install = install_generated_site_dependencies()

    if not install["ok"]:
        return {
            "ok": False,
            "install": install,
            "stdout": "",
            "stderr": install["stderr"],
            "returncode": install["returncode"],
        }

    # Start Vite Dev Server if not already running
    if vite_dev_process is None or vite_dev_process.poll() is not None:
        logger.info("Starting Vite Dev Server on port 5174...")
        vite_dev_process = subprocess.Popen(
            [
                "npm.cmd",
                "run",
                "dev",
                "--",
                "--port",
                "5174",
                "--strictPort",
                "--host"
            ],
            cwd=GENERATED_SITE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return {
        "ok": True,
        "install": install,
        "stdout": "Vite dev server is running on port 5174.",
        "stderr": "",
        "returncode": 0,
    }


def read_generated_source_files() -> dict[str, str]:
    if not os.path.isdir(GENERATED_SITE_DIR):
        return {}

    ignored_dirs = {
        "node_modules",
        "dist",
        ".vite",
    }
    allowed_extensions = {
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".css",
        ".html",
        ".json",
    }
    files: dict[str, str] = {}

    for root, dirs, names in os.walk(GENERATED_SITE_DIR):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in ignored_dirs
        ]

        for name in names:
            if name in {
                "package-lock.json",
                "tsconfig.app.tsbuildinfo",
                "tsconfig.node.tsbuildinfo",
            }:
                continue

            full_path = os.path.join(root, name)
            relative_path = os.path.relpath(
                full_path,
                GENERATED_SITE_DIR
            ).replace(os.sep, "/")

            if not any(name.endswith(extension) for extension in allowed_extensions):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as file:
                    files[relative_path] = file.read()
            except UnicodeDecodeError:
                continue

    return dict(
        sorted(files.items())
    )


def finalize_generation_result() -> dict:
    build = build_generated_site()
    files = read_generated_source_files()
    version = int(time.time())

    return {
        "files": files,
        "file_count": len(files),
        "preview_url": f"http://localhost:5174/",
        "build": build,
    }


def finalize_partial_generation_result() -> dict:
    ensure_generated_site_entrypoints()
    copy_generated_assets()
    normalize_generated_package_json()
    install = install_generated_site_dependencies()

    if not install["ok"]:
        return {
            "files": read_generated_source_files(),
            "file_count": len(read_generated_source_files()),
            "preview_url": None,
            "build": {
                "ok": False,
                "stdout": install["stdout"],
                "stderr": install["stderr"],
            },
            "partial": True,
        }

    result = finalize_generation_result()
    result["partial"] = True
    return result


@app.post("/generate")
def generate(request: PromptRequest):
    raise HTTPException(
        status_code=410,
        detail="Direct generation is disabled. Create and approve a wireframe first.",
    )


@app.post("/design-preview")
async def design_preview(request: PromptRequest):
    """Generate a reviewable wireframe without starting asset or code generation."""
    try:
        run_design_preview_async, _, _ = load_design_runners()
        state = await run_design_preview_async(
            prompt=request.prompt,
            selected_style=request.selected_style,
        )
        # Start with one page. Additional pages are generated explicitly by
        # the user so each request stays focused and independently editable.
        state["page_design_output"] = state["page_design_output"].model_copy(
            update={"pages": state["page_design_output"].pages[:1]}
        )
        session_id = uuid.uuid4().hex
        design_sessions[session_id] = {
            "state": state,
            "status": "wireframe_ready",
            "selected_asset_ids": [],
        }
        return _session_payload(session_id, design_sessions[session_id])
    except Exception as exc:
        logger.exception("Design preview generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/design-sessions/{session_id}")
def get_design_session(session_id: str):
    return _session_payload(session_id, _get_design_session(session_id))


@app.post("/design-sessions/{session_id}/pages")
async def add_design_page(session_id: str, request: AddPageRequest):
    """Generate one additional page from its own prompt and append it to the session."""
    session = _get_design_session(session_id)
    if session["status"] not in ("wireframe_ready", "page_code_review", "pages_complete"):
        raise HTTPException(status_code=409, detail="Add pages before starting asset selection.")

    try:
        run_design_preview_async, _, _ = load_design_runners()
        page_state = await run_design_preview_async(
            prompt=request.prompt,
            selected_style=session["state"]["selected_style"],
        )
        new_page = page_state["page_design_output"].pages[0]
        existing_names = {
            page.page_name for page in session["state"]["page_design_output"].pages
        }
        if new_page.page_name in existing_names:
            new_page = new_page.model_copy(update={
                "page_name": f"{new_page.page_name} {len(existing_names) + 1}"
            })
        current = session["state"]["page_design_output"]
        session["state"]["page_design_output"] = current.model_copy(
            update={"pages": [*current.pages, new_page]}
        )
        session["approved_pages"] = [
            page_name
            for page_name in session.get("approved_pages", [])
            if page_name in existing_names
        ]
        if session["status"] == "pages_complete":
            session["status"] = "page_code_review"

        from agents.page_code_agent import PageCodeAgent
        agent = PageCodeAgent()
        await agent.generate_project_shell(session["state"])

        return _session_payload(session_id, session)
    except Exception as exc:
        logger.exception("Additional page generation failed for session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/edit-section")
async def edit_design_section(
    session_id: str,
    request: SectionEditRequest,
):
    """Apply an AI edit to one draft section while leaving every other section intact."""
    session = _get_design_session(session_id)
    if session["status"] != "wireframe_ready":
        raise HTTPException(status_code=409, detail="Create a new draft to edit the wireframe structure.")

    page_design = next(
        (page for page in session["state"]["page_design_output"].pages if page.page_name == request.page_name),
        None,
    )
    if page_design is None:
        raise HTTPException(status_code=404, detail="Wireframe page not found.")

    section_index = next(
        (index for index, section in enumerate(page_design.sections) if section.order == request.section_order),
        None,
    )
    if section_index is None:
        raise HTTPException(status_code=404, detail="Wireframe section not found.")

    current_section = page_design.sections[section_index]
    try:
        from agents.json_utils import parse_model_json
        from agents.llm import deepseek_llm
        from agents.resilient_llm import resilient_ainvoke
        from langchain_core.messages import HumanMessage, SystemMessage
        from schema.page_d import SectionDesign

        response = await resilient_ainvoke(
            deepseek_llm,
            [
                SystemMessage(content=(
                    "You edit one website wireframe section. Return only valid JSON matching "
                    "the SectionDesign schema. Preserve the section order exactly. Do not add "
                    "or remove pages or other sections. Do not generate code."
                )),
                HumanMessage(content=json.dumps({
                    "current_section": current_section.model_dump(mode="json"),
                    "user_instruction": request.instruction,
                })),
            ],
            "section_wireframe_edit",
        )
        updated_section = parse_model_json(SectionDesign, response.content)
        updated_section = updated_section.model_copy(update={"order": current_section.order})
        page_design.sections[section_index] = updated_section
        return _session_payload(session_id, session)
    except Exception as exc:
        logger.exception("Section edit failed for design session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/approve")
async def approve_design(session_id: str):
    """Approve the wireframe: generate the project shell so page code can be generated per-page."""
    session = _get_design_session(session_id)
    if session["status"] != "wireframe_ready":
        raise HTTPException(status_code=409, detail="Session is not in wireframe_ready state.")
    try:
        from agents.page_code_agent import PageCodeAgent

        state = session["state"]
        # Ensure output dirs exist
        for directory in [
            os.path.join(PROJECT_ROOT, "generated_site"),
            os.path.join(PROJECT_ROOT, "generated_site", "src"),
            os.path.join(PROJECT_ROOT, "generated_site", "src", "components"),
            os.path.join(PROJECT_ROOT, "generated_site", "src", "pages"),
            os.path.join(PROJECT_ROOT, "generated_site", "src", "hooks"),
            os.path.join(PROJECT_ROOT, "generated_site", "src", "lib"),
            os.path.join(PROJECT_ROOT, "generated_site", "src", "assets"),
            os.path.join(PROJECT_ROOT, "generated_site", "public"),
        ]:
            os.makedirs(directory, exist_ok=True)

        agent = PageCodeAgent()
        await agent.generate_project_shell(state)

        # Track which pages have been approved
        session["approved_pages"] = []
        session["status"] = "page_code_review"
        return _session_payload(session_id, session)
    except Exception as exc:
        logger.exception("Project shell generation failed for design session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/generate-page-code")
async def generate_page_code(
    session_id: str,
    request: PageCodeRequest,
):
    """Generate (or regenerate) the React code for a single page."""
    session = _get_design_session(session_id)
    editable_statuses = (
        "page_code_review",
        "pages_complete",
        "asset_selection_ready",
        "asset_options_ready",
        "completed",
    )
    if session["status"] not in editable_statuses:
        raise HTTPException(
            status_code=409,
            detail="Approve the wireframe before generating page code.",
        )
    try:
        from agents.page_code_agent import PageCodeAgent
        agent = PageCodeAgent()
        
        max_attempts = 3
        last_error = ""
        
        for attempt in range(max_attempts):
            # If we had a build error on a previous attempt, pass it as a repair instruction
            current_instruction = request.instruction
            if attempt > 0 and last_error:
                repair_msg = (
                    f"Your previous attempt generated broken code that failed to build. "
                    f"Syntax error detected:\n{last_error}\n\n"
                    f"Please fix the syntax error and completely rewrite the file. Do not truncate the file."
                )
                current_instruction = (
                    f"{current_instruction}\n\n{repair_msg}" if current_instruction else repair_msg
                )

            await agent.generate_single_page(
                session["state"],
                page_name=request.page_name,
                instruction=current_instruction,
            )
            
            # Ensure vite dev server is running so frontend can iframe it
            ensure_generated_site_entrypoints()
            normalize_generated_package_json()
            build_generated_site()

            # Visual QA Step: Run a synchronous build to verify syntax/types
            build_result = subprocess.run(
                ["npm.cmd", "run", "build"],
                cwd=GENERATED_SITE_DIR,
                capture_output=True,
                text=True
            )
            
            if build_result.returncode == 0:
                # A regenerated page needs its own review again. Keep every other
                # page approved, so a small edit never restarts the whole workflow.
                approved_pages = session.setdefault("approved_pages", [])
                if request.page_name in approved_pages:
                    approved_pages.remove(request.page_name)
                session["status"] = "page_code_review"
                return {
                    "session_id": session_id,
                    "page_name": request.page_name,
                    "preview_url": "http://localhost:5174/",
                    "status": "ok",
                    "session": _session_payload(session_id, session),
                }
            
            # Build failed, record the error and try again
            last_error = build_result.stderr or build_result.stdout
            logger.error("Page code generation failed build on attempt %d for page %s:\n%s", attempt + 1, request.page_name, last_error)
            
        # If we exhausted all attempts
        logger.error("Page code generation resulted in permanently broken code for page %s", request.page_name)
        raise RuntimeError(f"Generated code failed to build after {max_attempts} attempts. Syntax error detected.\n{last_error}")

    except Exception as exc:
        logger.exception("Page code generation failed for session %s, page %s", session_id, request.page_name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/approve-page")
async def approve_page(
    session_id: str,
    request: PageCodeRequest,
):
    """Mark a page as approved and, once all pages are approved, transition to pages_complete."""
    session = _get_design_session(session_id)
    if session["status"] != "page_code_review":
        raise HTTPException(status_code=409, detail="Session is not in page_code_review state.")

    approved = session.setdefault("approved_pages", [])
    if request.page_name not in approved:
        approved.append(request.page_name)

    all_pages = [p.page_name for p in session["state"]["page_design_output"].pages]
    all_approved = all(p in approved for p in all_pages)

    if all_approved:
        session["status"] = "pages_complete"

    payload = _session_payload(session_id, session)
    payload["approved_pages"] = approved
    return payload


@app.post("/design-sessions/{session_id}/start-asset-phase")
async def start_asset_phase(session_id: str):
    """Manually trigger asset planning once all pages are approved."""
    session = _get_design_session(session_id)
    if session["status"] not in ("pages_complete", "page_code_review"):
        raise HTTPException(status_code=409, detail="All pages must be approved before starting asset planning.")

    try:
        _, plan_assets_async, _ = load_design_runners()
        await plan_assets_async(session["state"])
        session["status"] = "asset_selection_ready"
        return _session_payload(session_id, session)
    except Exception as exc:
        logger.exception("Asset planning failed for design session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/skip-assets")
async def skip_assets(session_id: str):
    """Skip the asset generation phase entirely and proceed to final completed state."""
    session = _get_design_session(session_id)
    if session["status"] not in ("pages_complete", "asset_selection_ready", "asset_options_ready"):
        raise HTTPException(status_code=409, detail="Must approve pages first to skip assets.")

    try:
        ensure_generated_site_entrypoints()
        normalize_generated_package_json()
        build_generated_site()
        
        result = finalize_generation_result()
        session["status"] = "completed"
        return {
            "session": _session_payload(session_id, session),
            "result": result,
        }
    except Exception as exc:
        logger.exception("Skip assets failed for session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/generate")
async def generate_approved_design(
    session_id: str,
    request: AssetSelectionRequest,
):
    """Generate only approved assets, then run the existing frontend code path."""
    session = _get_design_session(session_id)
    state = session["state"]
    asset_output = state.get("asset_output")

    generated_asset_output = state.get("generated_asset_output")
    if session["status"] != "asset_options_ready" or asset_output is None or generated_asset_output is None:
        raise HTTPException(
            status_code=409,
            detail="Approve the wireframe and generate asset options before generating code.",
        )

    valid_ids = {
        asset.asset_id for asset in generated_asset_output.assets
        if asset.status.value == "success" and not asset.asset_id.endswith("_source")
    }
    unknown_ids = set(request.asset_ids) - valid_ids
    if unknown_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown asset IDs: {', '.join(sorted(unknown_ids))}",
        )

    selected = [
        asset for asset in asset_output.assets
        if asset.asset_id in set(request.asset_ids)
    ]
    state["asset_output"] = asset_output.model_copy(update={"assets": selected})
    selected_ids = set(request.asset_ids)
    state["generated_asset_output"] = generated_asset_output.model_copy(update={
        "assets": [
            asset for asset in generated_asset_output.assets
            if asset.asset_id in selected_ids
            or asset.source_asset_id in selected_ids
        ]
    })
    session["selected_asset_ids"] = request.asset_ids

    try:
        _, _, run_approved_build_async = load_design_runners()
        await run_approved_build_async(state)
        result = finalize_generation_result()
        session["status"] = "completed"
        return {
            "session": _session_payload(session_id, session),
            "result": result,
        }
    except Exception as exc:
        logger.exception("Approved design generation failed for session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/generate-assets")
async def generate_asset_options(session_id: str):
    """Generate the approved asset plan so the user can select real files."""
    session = _get_design_session(session_id)
    if session["status"] != "asset_selection_ready":
        raise HTTPException(status_code=409, detail="Approve the wireframe before generating assets.")

    try:
        from agents.gen_agent import GenerationAgent

        output = await GenerationAgent().generate(session["state"]["asset_output"])
        session["state"]["generated_asset_output"] = output
        session["status"] = "asset_options_ready"
        return _session_payload(session_id, session)
    except Exception as exc:
        logger.exception("Asset option generation failed for session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/design-sessions/{session_id}/edit-asset")
async def edit_generated_asset(session_id: str, request: AssetEditRequest):
    """Regenerate only the selected image/video using a natural-language edit."""
    session = _get_design_session(session_id)
    state = session["state"]
    asset_output = state.get("asset_output")
    if session["status"] != "asset_options_ready" or asset_output is None:
        raise HTTPException(status_code=409, detail="Generate asset options before editing an asset.")

    original = next((asset for asset in asset_output.assets if asset.asset_id == request.asset_id), None)
    if original is None:
        raise HTTPException(status_code=404, detail="Asset requirement not found.")

    try:
        from agents.gen_agent import GenerationAgent

        edited = original.model_copy(update={
            "prompt": f"{original.prompt or ''}\nUser edit: {request.instruction}",
            "output_filename": f"{original.asset_id}_edited.{original.format.lstrip('.')}",
        })
        edited_output = await GenerationAgent().generate(
            asset_output.model_copy(update={"assets": [edited]})
        )
        existing = state.get("generated_asset_output")
        if existing is not None:
            removed_ids = {request.asset_id, f"{request.asset_id}_source"}
            merged = [asset for asset in existing.assets if asset.asset_id not in removed_ids]
            merged.extend(edited_output.assets)
            state["generated_asset_output"] = existing.model_copy(update={"assets": merged})
        else:
            state["generated_asset_output"] = edited_output
        return _session_payload(session_id, session)
    except Exception as exc:
        logger.exception("Asset edit failed for session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate-stream")
async def generate_stream(request: PromptRequest):
    raise HTTPException(
        status_code=410,
        detail="Direct generation is disabled. Create and approve a wireframe first.",
    )

    async def stream():
        try:
            _, run_graph_events = load_graph_runners()

            async for event in run_graph_events(
                prompt=request.prompt,
                selected_style=request.selected_style,
            ):
                if event.get("type") == "state":
                    continue

                yield _sse(event)

            yield _sse(
                {
                    "type": "step",
                    "step": "dependencies",
                    "label": "Installing generated site dependencies",
                    "status": "started",
                }
            )

            ensure_generated_site_entrypoints()
            copy_generated_assets()
            normalize_generated_package_json()
            install = install_generated_site_dependencies()

            yield _sse(
                {
                    "type": "step",
                    "step": "dependencies",
                    "label": "Installing generated site dependencies",
                    "status": "completed" if install["ok"] else "warning",
                }
            )

            if not install["ok"]:
                yield _sse(
                    {
                        "type": "error",
                        "message": f"Dependency install failed: {install['stderr'] or install['stdout']}",
                    }
                )
                return

            yield _sse(
                {
                    "type": "step",
                    "step": "preview",
                    "label": "Starting dev server",
                    "status": "started",
                }
            )

            result = finalize_generation_result()

            yield _sse(
                {
                    "type": "step",
                    "step": "preview",
                    "label": "Building preview bundle",
                    "status": "completed" if result["build"]["ok"] else "warning",
                }
            )
            yield _sse(
                {
                    "type": "result",
                    "result": result,
                }
            )
        except Exception as exc:
            logger.exception("Streaming generation failed")
            try:
                partial_result = finalize_partial_generation_result()
                yield _sse(
                    {
                        "type": "step",
                        "step": "partial_preview",
                        "label": "Publishing partial generated preview",
                        "status": (
                            "completed"
                            if partial_result["build"]["ok"]
                            else "warning"
                        ),
                    }
                )
                yield _sse(
                    {
                        "type": "result",
                        "result": partial_result,
                    }
                )
            except Exception:
                logger.exception("Partial preview publishing failed")

            yield _sse(
                {
                    "type": "error",
                    "message": str(exc),
                }
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
    )



import urllib.parse
import httpx
import aiofiles
from fastapi import UploadFile, File

@app.get("/design-sessions/{session_id}/assets/plan")
async def get_asset_plan(session_id: str):
    """Return the asset plan already created for this design session."""
    session = _get_design_session(session_id)
    asset_output = session["state"].get("asset_output")
    if asset_output is None:
        raise HTTPException(
            status_code=409,
            detail="Asset planning has not started for this design session.",
        )

    return asset_output.model_dump(mode="json")


@app.get("/design-sessions/{session_id}/pages/placements")
async def get_page_placements(session_id: str):
    """
    Scan all generated page TSX files and return every data-asset-id found,
    grouped by page. The frontend uses this to populate Page + Section dropdowns.
    """
    import re as _re
    pages_dir = os.path.join(GENERATED_SITE_DIR, "src", "pages")
    if not os.path.isdir(pages_dir):
        return {"placements": []}

    # Regex to capture data-asset-id="..." and optionally the closest heading/section context
    asset_id_pattern = _re.compile(r'data-asset-id=["\']([^"\']+)["\']')
    # Try to guess a human-readable section name from surrounding context
    section_context_pattern = _re.compile(
        r'(?:id|aria-label|data-section)[=:\s]*["\']([^"\']{2,60})["\']'
    )

    placements = []
    for filename in sorted(os.listdir(pages_dir)):
        if not filename.endswith((".tsx", ".jsx")):
            continue
        page_name = os.path.splitext(filename)[0]
        page_path = os.path.join(pages_dir, filename)
        try:
            with open(page_path, "r", encoding="utf-8") as fh:
                source = fh.read()
        except OSError:
            continue

        sections = []
        # Walk through all data-asset-id occurrences with surrounding context
        for m in asset_id_pattern.finditer(source):
            aid = m.group(1)
            # Look at 300 chars before the match for a section/aria-label hint
            context_window = source[max(0, m.start() - 300): m.start()]
            ctx_match = section_context_pattern.search(context_window)
            section_label = ctx_match.group(1) if ctx_match else aid.replace("_", " ").title()
            sections.append({"asset_id": aid, "section_name": section_label})

        if sections:
            placements.append({"page_name": page_name, "sections": sections})

    return {"placements": placements}


class GenerateAssetRequest(BaseModel):
    prompt: str
    edit_request: Optional[str] = None
    is_video: Optional[bool] = False
    width: int
    height: int

@app.post("/design-sessions/{session_id}/assets/{asset_id}/generate")
async def generate_single_asset(session_id: str, asset_id: str, request: GenerateAssetRequest):
    final_prompt = request.prompt
    if request.edit_request:
        agent = AssetAgent()
        final_prompt = await agent.process_edit_request(request.prompt, request.edit_request)
        
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
        
    if request.is_video:
        provider = PollinationsProvider()
        await provider.connect()
        try:
            image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_prompt)}?width={request.width}&height={request.height}&nologo=true"
            video_bytes = await provider.generate_video(
                prompt=final_prompt,
                image_url=image_url
            )
            filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.mp4")
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(video_bytes)
        finally:
            await provider.close()
        return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.mp4", "revised_prompt": final_prompt}

    encoded_prompt = urllib.parse.quote(final_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={request.width}&height={request.height}&nologo=true"
    filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0)
        response.raise_for_status()
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(response.content)
            
    return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.png", "revised_prompt": final_prompt}

@app.post("/design-sessions/{session_id}/assets/{asset_id}/upload")
async def upload_single_asset(session_id: str, asset_id: str, file: UploadFile = File(...)):
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
    filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png") # Save as png so injection agent finds it easily
    
    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)
        
    return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.png"}

# Session-less endpoints for free-mode Asset Studio (no pages required)
@app.post("/assets/{asset_id}/generate")
async def generate_free_asset(asset_id: str, request: GenerateAssetRequest):
    final_prompt = request.prompt
    if request.edit_request:
        agent = AssetAgent()
        final_prompt = await agent.process_edit_request(request.prompt, request.edit_request)
        
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
        
    if request.is_video:
        provider = PollinationsProvider()
        await provider.connect()
        try:
            image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_prompt)}?width={request.width}&height={request.height}&nologo=true"
            video_bytes = await provider.generate_video(
                prompt=final_prompt,
                image_url=image_url
            )
            filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.mp4")
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(video_bytes)
        finally:
            await provider.close()
        return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.mp4", "revised_prompt": final_prompt}

    encoded_prompt = urllib.parse.quote(final_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={request.width}&height={request.height}&nologo=true"
    filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0)
        response.raise_for_status()
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(response.content)
            
    return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.png", "revised_prompt": final_prompt}

@app.post("/assets/{asset_id}/upload")
async def upload_free_asset(asset_id: str, file: UploadFile = File(...)):
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
    filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png")
    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)
    return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.png"}

class InjectAssetConfig(BaseModel):
    asset_id: str
    target_asset_id: Optional[str] = None
    page_name: Optional[str] = None
    is_parallax: bool
    
class InjectAssetsRequest(BaseModel):
    assets: list[InjectAssetConfig]

@app.post("/design-sessions/{session_id}/assets/inject")
async def inject_assets_endpoint(session_id: str, request: InjectAssetsRequest):
    from agents.asset_injection_agent import AssetInjectionAgent
    agent = AssetInjectionAgent()
    
    # We pass the user configs to the injection agent
    # Since inject_assets doesn't take args currently, we write a temporary config file for it
    config_path = os.path.join(GENERATED_ASSETS_DIR, "injection_config.json")
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(request.model_dump_json())
        
    await agent.inject_assets() 
    
    ensure_generated_site_entrypoints()
    normalize_generated_package_json()
    build_generated_site()
    
    session = _get_design_session(session_id)
    
    return {
        "status": "ok",
        "session": _session_payload(session_id, session),
        "preview_url": "http://localhost:5174/",
    }


frontend_dist = os.path.join(os.path.dirname(__file__), "frontend/dist")
assets_dir = os.path.join(frontend_dist, "assets")
generated_preview_root = os.path.abspath(GENERATED_SITE_DIST)

if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

if os.path.isdir(GENERATED_ASSETS_DIR):
    app.mount(
        "/generated-assets",
        StaticFiles(directory=GENERATED_ASSETS_DIR),
        name="generated-assets",
    )


from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse

@app.get("/generated-preview/{full_path:path}")
def generated_preview(full_path: str):
    # Redirect all requests to the Vite Dev Server
    return RedirectResponse(f"http://localhost:5174/{full_path}")


@app.get("/{full_path:path}")
def catch_all(full_path: str):
    index_file = os.path.join(frontend_dist, "index.html")

    if not os.path.isfile(index_file):
        raise HTTPException(status_code=404, detail="Frontend build not found")

    return FileResponse(index_file)
