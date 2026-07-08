import logging
import os
import hashlib
import json
import shutil
import subprocess
import time
from typing import ClassVar

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator


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


class PromptRequest(BaseModel):
    VALID_STYLES: ClassVar[set[str]] = {
        "glassmorphism",
        "skeuomorphism",
        "claymorphism",
        "minimalism",
        "liquid_glass",
        "neo_brutalism",
    }

    prompt: str = Field(min_length=1, max_length=12000)
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
    try:
        run_graph, _ = load_graph_runners()
        run_graph(prompt=request.prompt, selected_style=request.selected_style)
        result = finalize_generation_result()
        return {"result": result}
    except Exception as exc:
        logger.exception("Generation request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate-stream")
async def generate_stream(request: PromptRequest):
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


frontend_dist = os.path.join(os.path.dirname(__file__), "frontend/dist")
assets_dir = os.path.join(frontend_dist, "assets")
generated_preview_root = os.path.abspath(GENERATED_SITE_DIST)

if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


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
