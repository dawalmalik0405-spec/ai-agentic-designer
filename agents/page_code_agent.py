from schema.code import CodeGenerationInput
from agents.llm import gemini_flash_llm
from pipeline_utils import resilient_ainvoke
from mcp_tools.initialize_mcps import run_mcp_agent
from langchain_core.messages import HumanMessage, SystemMessage
import os
import re
import json
import logging
import asyncio
import subprocess
import sys
import threading
import queue
import socket
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "generated_site")

# Global to track the running Vite dev server process across generations
DEV_SERVER_PROCESS = None

# How long to wait for "npm run dev" to report it's ready before giving up.
DEV_SERVER_READY_TIMEOUT = 30
# Strings Vite prints once the dev server is actually serving requests.
DEV_SERVER_READY_MARKERS = ("ready in", "Local:")


class CodePromptBuilder:
    """Builds strict prompts for the Code Agent enforcing single responsibility."""

    @staticmethod
    def build_system_prompt() -> str:
        return """You are the Code Generation Agent.

Your only responsibility is to convert the provided Design System and Page Blueprint into a production-ready React + TypeScript page component.

You are NOT a designer, planner, or architect. All design decisions have already been made by previous agents. Your job is to implement them faithfully.

==========================================================
PRIMARY RESPONSIBILITIES
==========================================================

- Generate one complete React TSX page component.
- Implement the supplied Page Blueprint exactly.
- Follow the supplied Design System exactly.
- Produce clean, readable, production-quality React code.
- Export a single default React component.

==========================================================
STRICT BOUNDARIES
==========================================================

DO NOT redesign the page.

DO NOT invent new sections.

DO NOT remove sections.

DO NOT add sections.

DO NOT change layouts.

DO NOT change typography.

DO NOT change spacing.

DO NOT change colors.

DO NOT change content.

DO NOT rewrite copy.

DO NOT generate placeholder text.

DO NOT generate placeholder images.

DO NOT generate assets.

DO NOT generate SVG illustrations.

DO NOT generate animations.

DO NOT use GSAP.

DO NOT use Framer Motion.

DO NOT implement parallax or scroll effects.

DO NOT edit previously generated files.

DO NOT generate package.json.

DO NOT generate CSS files.

DO NOT generate configuration files.

Assume the project structure already exists.

==========================================================
HEROUI — MANDATORY TOOL USE
==========================================================
You have access to HeroUI MCP tools. You MUST use them, not your own memory of
HeroUI, whenever a HeroUI component is needed. Concretely, before writing any
JSX that references a HeroUI component:

1. List every HeroUI component the blueprint requires.
2. For each one, call the HeroUI MCP documentation tool exactly once to fetch
   its real props, exports, and usage example.
3. If the component needs a context Provider (e.g. a form, modal, or table
   provider), fetch that provider's documentation too, before using it.
4. Only use component names, props, and exports that the MCP tool actually
   returned. Never assume an export or prop exists because it "sounds right"
   or matches an older version you remember.
5. Do not call the same component's documentation tool more than once.
6. Once you have documentation for every HeroUI component the page needs,
   stop calling tools and generate the page immediately.

If a required HeroUI component cannot be found via the MCP tool, fall back to
a plain Tailwind-styled native element instead of guessing at a HeroUI API.

Rules:

- Use HeroUI whenever an equivalent component exists.
- Use Tailwind CSS only for layout, spacing, sizing and small visual adjustments.

==========================================================
CODE QUALITY
==========================================================

Generate idiomatic React 19.

Use TypeScript.

Use functional components.

Prefer reusable JSX where appropriate inside the page.

Avoid unnecessary state.

Avoid unnecessary effects.

Avoid unnecessary abstractions.

Generate code that compiles without modification.

==========================================================
OUTPUT FORMAT
==========================================================

Return ONLY one complete React TSX page component.

Return nothing except a single ```tsx``` code block.

The component must:

- export default
- compile successfully
- contain all imports
- contain no explanations
- contain no markdown outside the code block
- contain no comments describing what you did

Never generate additional files.
Never describe your reasoning.
Never explain your choices.

"""

    @staticmethod
    def build_user_prompt(page_blueprint, design_system, style_guidance: str, instruction: str = None) -> str:
        prompt = f"""
Generate one production-ready React TSX page component.

Implement the following Page Blueprint exactly.

Use the supplied Design System exactly.

Do not redesign the page.

Do not invent content.

Do not add or remove sections.

Do not generate assets.

Do not generate animations.

Style Guidance:
{style_guidance}

Design System:
{design_system}

Page Blueprint:
{page_blueprint}
"""
        if instruction:
            prompt += f"\n\nUSER EDIT INSTRUCTION:\n{instruction}\nModify the page specifically to address this instruction."

        return prompt

    @staticmethod
    def build_repair_system_prompt() -> str:
        return """You are the Code Repair Agent.

Your only job is to fix compile/build errors in an existing React + TypeScript file.

RULES:
- Fix ONLY the listed compile errors.
- Preserve layout, copy, design, sections, and styling unless a fix requires a minimal change.
- Return the COMPLETE corrected file, not a diff or partial snippet.
- Use valid HeroUI component props — consult HeroUI MCP tools if needed.
- The file must compile with TypeScript and export default if it is a page component.
- Return ONLY one ```tsx``` code block with the full file contents.
- Do not add explanations outside the code block.
"""

    @staticmethod
    def build_repair_user_prompt(
        relative_path: str,
        original_code: str,
        errors: list,
    ) -> str:
        error_lines = []
        for err in errors:
            location = ""
            if err.line is not None and err.column is not None:
                location = f" ({err.line},{err.column})"
            code_prefix = f"{err.code}: " if err.code else ""
            error_lines.append(f"- {err.file}{location}: {code_prefix}{err.message}")

        return f"""Repair this file so it compiles successfully.

File: {relative_path}

Compile errors to fix:
{chr(10).join(error_lines)}

Current file contents:
```tsx
{original_code}
```

Return the complete corrected file.
"""

    @staticmethod
    def build_app_shell_system_prompt() -> str:
        return """You are the App Shell Code Agent.

Your responsibility is to generate the complete src/main.tsx entry file for a multi-page React site.

This file MUST include:
- All page imports and React Router routes for every supplied page
- A site header with navigation links for every page
- Navigation styled according to the Design System and navigation_style guidance
- The createRoot bootstrap with BrowserRouter and Providers

RULES:
- Use the Design System colors, typography, and spacing for the navbar/header
- Navigation link labels must be human-readable plain text (no JSON quotes in JSX text)
- Use NavLink from react-router-dom for navigation with active-state styling
- Import Providers from "./providers"
- Import "./index.css"
- Include a catch-all route redirecting to the home page
- Use HeroUI MCP tools when HeroUI components fit the navigation design
- Return ONLY one complete ```tsx``` code block containing the full main.tsx file
- The file must compile without modification
- Do not use placeholder text or lorem ipsum in the navbar
"""

    @staticmethod
    def build_app_shell_user_prompt(
        page_info: list[dict],
        design_system,
        navigation_style: str,
        style_guidance: str,
        instruction: str | None = None,
    ) -> str:
        pages_json = json.dumps(page_info, indent=2)
        prompt = f"""Generate the complete src/main.tsx app shell for this website.

Style Guidance:
{style_guidance}

Navigation Style:
{navigation_style}

Design System:
{design_system}

Pages (use these exact module names, routes, and labels):
{pages_json}

Requirements:
- Import each page from "./pages/{{ModuleName}}"
- Create a polished, brand-consistent header/nav using the design system
- Wire every page into React Router
- Link labels must match the "label" field exactly (plain text, no surrounding quotes)
"""
        if instruction:
            prompt += f"\n\nAdditional instruction:\n{instruction}\n"
        return prompt


class ProjectShellGenerator:
    """Generates the foundational React project files synchronously."""

    @staticmethod
    def _is_dark_hex_color(color: str) -> bool:
        if not isinstance(color, str) or not color.startswith("#"):
            return False
        hex_value = color.lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) != 6:
            return False
        try:
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)
        except ValueError:
            return False
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness < 128

    @staticmethod
    def _module_name(name: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", name)
        if not words:
            return "Page"
        return "".join(word[:1].upper() + word[1:] for word in words)

    @staticmethod
    def _route_path(page_name: str, index: int) -> str:
        if index == 0:
            return "/"
        words = re.findall(r"[A-Za-z0-9]+", page_name.lower())
        return "/" + "-".join(words)

    @staticmethod
    def build_page_info(pages, existing_pages: list | None = None) -> list[dict]:
        """Build routing metadata for app shell generation."""
        all_pages = list(existing_pages or []) + list(pages)
        page_info = []
        for index, page in enumerate(all_pages):
            page_name = page.page_name if hasattr(page, "page_name") else page.get("page_name")
            page_info.append({
                "module": ProjectShellGenerator._module_name(page_name),
                "route": ProjectShellGenerator._route_path(page_name, index),
                "label": page_name.strip(),
            })
        return page_info

    def generate_shell(self, state: dict) -> str:
        directories = [
            "src/components",
            "src/pages",
            "src/hooks",
            "src/lib",
            "src/assets",
            "public",
        ]
        for directory in directories:
            os.makedirs(os.path.join(OUTPUT_DIR, directory), exist_ok=True)

        design_output = state.get("design_system_output")

        package = {
            "name": "generated-website",
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc -b && vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "@heroui/react": "^3.2.4",
                "framer-motion": "^13.0.0",
                "lucide-react": "^1.30.0",
                "react": "^19.2.8",
                "react-dom": "^19.2.8",
                "react-router-dom": "^7.18.2"
            },
            "devDependencies": {
                "@tailwindcss/postcss": "^4.3.3",
                "@types/node": "^26.2.0",
                "@types/react": "^19.2.18",
                "@types/react-dom": "^19.2.4",
                "@vitejs/plugin-react": "^5.2.0",
                "autoprefixer": "^10.5.4",
                "postcss": "^8.5.26",
                "tailwindcss": "^4.3.3",
                "typescript": "^5.9.2",
                "vite": "^7.1.3"
            }
        }

        background = "#f8fafc"
        text = "#0f172a"
        if design_output:
            background = getattr(design_output.colors, "background", background)
            text = getattr(design_output.colors, "surface", text)
            if self._is_dark_hex_color(background):
                text = getattr(design_output.colors, "dark_surface", "#f7f2e8")

        index_css = f"""
@import "tailwindcss";

:root {{
  font-family: Inter, system-ui, sans-serif;
}}

html,
body,
#root {{
  width: 100%;
  min-height: 100%;
}}
* {{
    box-sizing: border-box;
}}
body {{
  margin: 0;
  background: {background};
  color: {text};
}}
"""

        files = {
            "package.json": json.dumps(package, indent=2) + "\n",
            "index.html": '<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="UTF-8" />\n    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n    <title>Generated Website</title>\n  </head>\n  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>\n</html>\n',
            "tsconfig.json": '{"files": [], "references": [{"path":"./tsconfig.app.json"},{"path":"./tsconfig.node.json"}]}\n',
            "tsconfig.app.json": '{\n  "compilerOptions": {"target":"ES2022","useDefineForClassFields":true,"lib":["ES2022","DOM","DOM.Iterable"],"skipLibCheck":true,"esModuleInterop":true,"allowSyntheticDefaultImports":true,"strict":true,"module":"ESNext","moduleResolution":"Bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx"},\n  "include": ["src"]\n}\n',
            "tsconfig.node.json": '{\n  "compilerOptions": {"composite":true,"skipLibCheck":true,"module":"ESNext","moduleResolution":"Bundler","types":["node"]},\n  "include": ["vite.config.ts"]\n}\n',
            "vite.config.ts": 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\nimport { fileURLToPath } from "node:url";\nimport path from "node:path";\nconst __dirname = path.dirname(fileURLToPath(import.meta.url));\nexport default defineConfig({ base: "/site-preview/", plugins:[react()], resolve:{ alias:{"@":path.resolve(__dirname,"src")} } });\n',
            "src/providers.tsx": """import type { ReactNode } from "react";
import { RouterProvider } from "@heroui/react";
import { useNavigate } from "react-router-dom";

export default function Providers({
  children,
}: {
  children: ReactNode;
}) {
  const navigate = useNavigate();

  return (
    <RouterProvider navigate={navigate}>
      {children}
    </RouterProvider>
  );
}
""",
            "postcss.config.js": """export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
""",
            "src/index.css": index_css,
        }

        for relative_path, content in files.items():
            filepath = os.path.join(OUTPUT_DIR, relative_path)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(content)

        return "Created project config shell (main.tsx generated separately by agent)."


class DevServerManager:
    """
    Manages npm install / npm run dev the way a person running them in a
    terminal would experience them: streamed output, readiness detected from
    Vite's own stdout instead of a fixed sleep().

    Deliberately built on subprocess.Popen + a background reader thread
    rather than asyncio.create_subprocess_exec. asyncio's subprocess support
    requires the Proactor event loop on Windows — if anything else in the
    process (uvicorn, another library) has switched to the Selector event
    loop, asyncio.create_subprocess_exec raises NotImplementedError. Popen
    has no such dependency on which event loop is running, so this works
    the same on every platform/loop combination. asyncio.to_thread() is used
    to keep these blocking calls off the event loop.
    """

    @staticmethod
    def _is_port_open(host: str = "127.0.0.1", port: int = 5173) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0

    @staticmethod
    def _reader_thread(process: subprocess.Popen, out_queue: "queue.Queue[str | None]") -> None:
        """Runs in a background thread: pushes each stdout line onto out_queue.
        Puts None once the process closes stdout (exited or crashed)."""
        try:
            assert process.stdout is not None
            for raw_line in process.stdout:
                out_queue.put(raw_line.rstrip())
        finally:
            out_queue.put(None)

    async def _drain_forever(self, out_queue: "queue.Queue[str | None]", label: str) -> None:
        """Background task: keep pulling lines off the queue and logging them
        for the lifetime of a long-running process (e.g. the dev server),
        so the OS pipe buffer never fills up and blocks the child process."""
        while True:
            line = await asyncio.to_thread(out_queue.get)
            if line is None:
                return
            if line:
                logger.info("[%s] %s", label, line)

    async def _run_streamed(self, cmd: list[str], cwd: str, label: str) -> tuple[int, list[str]]:
        """Run a command to completion, logging each line as it arrives."""
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        out_queue: "queue.Queue[str | None]" = queue.Queue()
        reader = threading.Thread(target=self._reader_thread, args=(process, out_queue), daemon=True)
        reader.start()

        lines: list[str] = []
        while True:
            line = await asyncio.to_thread(out_queue.get)
            if line is None:
                break
            if line:
                logger.info("[%s] %s", label, line)
                lines.append(line)

        returncode = await asyncio.to_thread(process.wait)
        reader.join(timeout=2)
        return returncode, lines

    async def _start_and_wait_ready(
        self, cmd: list[str], cwd: str, ready_markers: tuple[str, ...], timeout: int
    ) -> tuple[subprocess.Popen, bool, list[str], asyncio.Task]:
        """Start a long-running process (the dev server) and wait until one of
        ready_markers shows up in its stdout, or until timeout elapses.
        Returns the live process plus a background drain task that must be
        cancelled when the process is later stopped."""
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        out_queue: "queue.Queue[str | None]" = queue.Queue()
        reader = threading.Thread(target=self._reader_thread, args=(process, out_queue), daemon=True)
        reader.start()

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        lines: list[str] = []
        ready = False
        crashed = False

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                line = await asyncio.to_thread(out_queue.get, True, remaining)
            except queue.Empty:
                break

            if line is None:
                crashed = True
                break

            if line:
                logger.info("[vite] %s", line)
                lines.append(line)
                if any(marker in line for marker in ready_markers):
                    ready = True
                    break

        # Whether or not it's ready yet, keep draining stdout in the
        # background for as long as the process lives, so it never blocks
        # on a full pipe buffer once we stop actively watching for "ready".
        drain_task = asyncio.create_task(self._drain_forever(out_queue, "vite"))

        if crashed:
            process.wait()

        return process, ready, lines, drain_task

    async def install_and_start(self, output_dir: str) -> dict:
        global DEV_SERVER_PROCESS

        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

        # ----------------------------------
        # -----------------------------------------------------
        # Only install if node_modules isn't already there
        # -----------------------------------------------------
        node_modules = os.path.join(output_dir, "node_modules")

        if not os.path.exists(node_modules):
            logger.info("No node_modules found — running npm install in %s...", output_dir)
            install_returncode, install_lines = await self._run_streamed(
                [npm_cmd, "install", "--no-fund", "--no-audit"],
                cwd=output_dir,
                label="npm install",
            )

            if install_returncode != 0:
                return {
                    "build_status": "Failed during npm install",
                    "preview_url": None,
                    "project_path": output_dir,
                    "log_tail": install_lines[-40:],
                }
        else:
            logger.info("node_modules already present — skipping install.")

        if DEV_SERVER_PROCESS is not None:
            process, _ = DEV_SERVER_PROCESS
            if process.poll() is None:
                logger.info("Vite dev server already running — reusing it.")
                return {
                    "build_status": "Success",
                    "preview_url": "http://localhost:5173/site-preview/",
                    "project_path": output_dir,
                    "log_tail": ["Vite dev server already running."],
                }

        if self._is_port_open():
            logger.info("Port 5173 is already serving — reusing existing dev server.")
            return {
                "build_status": "Success",
                "preview_url": "http://localhost:5173/site-preview/",
                "project_path": output_dir,
                "log_tail": ["Port 5173 is already serving."],
            }

        # -----------------------------------------------------
        # Stop any previously running dev server before starting a new one
        # -----------------------------------------------------
        if DEV_SERVER_PROCESS is not None:
            logger.info("Stopping existing Vite dev server...")
            old_process, old_drain_task = DEV_SERVER_PROCESS
            try:
                old_process.terminate()
                try:
                    await asyncio.to_thread(old_process.wait, 5)
                except subprocess.TimeoutExpired:
                    old_process.kill()
                    await asyncio.to_thread(old_process.wait)
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning("Failed to stop existing dev server: %s", e)
            old_drain_task.cancel()
            DEV_SERVER_PROCESS = None

        # -----------------------------------------------------
        # Start `npm run dev`, same as a person typing it in a terminal,
        # and wait until Vite itself reports it's serving requests.
        # -----------------------------------------------------
        logger.info("Starting npm run dev in %s...", output_dir)
        process, ready, startup_lines, drain_task = await self._start_and_wait_ready(
            [npm_cmd, "run", "dev", "--", "--port", "5173", "--strictPort"],
            cwd=output_dir,
            ready_markers=DEV_SERVER_READY_MARKERS,
            timeout=DEV_SERVER_READY_TIMEOUT,
        )
        DEV_SERVER_PROCESS = (process, drain_task)

        if process.poll() is not None:
            # The process already exited — it crashed on startup.
            drain_task.cancel()
            DEV_SERVER_PROCESS = None
            return {
                "build_status": "Dev server exited during startup",
                "preview_url": None,
                "project_path": output_dir,
                "log_tail": startup_lines[-40:],
            }

        if not ready:
            return {
                "build_status": f"Dev server did not report ready within {DEV_SERVER_READY_TIMEOUT}s",
                "preview_url": None,
                "project_path": output_dir,
                "log_tail": startup_lines[-40:],
            }

        return {
            "build_status": "Success",
            "preview_url": "http://localhost:5173/site-preview/",   
            "project_path": output_dir,
        }



    def get_status(self) -> dict:
        """Reports whether the dev server is already running, without touching npm."""
        global DEV_SERVER_PROCESS
        if DEV_SERVER_PROCESS is not None:
            process, _ = DEV_SERVER_PROCESS
            if process.poll() is None:  # still alive
                return {"running": True, "preview_url": "http://localhost:5173/site-preview/"}
        if self._is_port_open():
            return {"running": True, "preview_url": "http://localhost:5173/site-preview/"}
        return {"running": False, "preview_url": None}


class PageCodeAgent:
    """Orchestrator Agent for generating React code."""

    def __init__(self):
        self.model = gemini_flash_llm()
        self.shell_generator = ProjectShellGenerator()
        self.prompt_builder = CodePromptBuilder()
        self.server_manager = DevServerManager()

    @staticmethod
    def _extract_tsx(response) -> str:
        content = getattr(response, "content", str(response))

        if isinstance(content, list):
            content = "".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in content
            )

        match = re.search(
            r"```(?:tsx|typescript|jsx|javascript)?\s*(.*?)```",
            content,
            re.DOTALL,
        )

        code = match.group(1).strip() if match else content.strip()

        if "export default" not in code:
            raise ValueError(
                f"Model didn't return a TSX component.\n\n{content}"
            )

        return code

    @staticmethod
    def _extract_generated_file(response) -> str:
        """Extract a full TSX/TS module (pages or main.tsx) from model output."""
        content = getattr(response, "content", str(response))

        if isinstance(content, list):
            content = "".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in content
            )

        match = re.search(
            r"```(?:tsx|typescript|jsx|javascript|ts)?\s*(.*?)```",
            content,
            re.DOTALL,
        )
        code = match.group(1).strip() if match else content.strip()

        if not code:
            raise ValueError(f"Model returned empty file content.\n\n{content}")

        return code

    async def generate_project_shell(self, state: dict) -> str:
        """Called by nodes.py to create config files (package.json, vite, css, etc.)."""
        return self.shell_generator.generate_shell(state)

    async def generate_app_shell(
        self,
        state: dict,
        existing_pages: list | None = None,
        instruction: str | None = None,
    ) -> dict:
        """Generate src/main.tsx with agent-designed navigation and routing."""
        page_design = state.get("page_design_output")
        if not page_design or not page_design.pages:
            raise ValueError("page_design_output is required to generate app shell.")

        page_info = ProjectShellGenerator.build_page_info(
            page_design.pages,
            existing_pages=existing_pages,
        )
        design_sys = state.get("design_system_output") or state.get("existing_design_system_output")
        navigation_style = "Modern responsive navigation with clear page links."
        global_rules = page_design.global_rules
        if existing_pages and state.get("existing_page_design_output"):
            global_rules = state["existing_page_design_output"].global_rules
        if global_rules:
            navigation_style = global_rules.navigation_style

        style = state.get("selected_style", "default")
        system_prompt = self.prompt_builder.build_app_shell_system_prompt()
        user_prompt = self.prompt_builder.build_app_shell_user_prompt(
            page_info=page_info,
            design_system=design_sys,
            navigation_style=navigation_style,
            style_guidance=style,
            instruction=instruction,
        )

        logger.info("Generating app shell (main.tsx) with %d pages...", len(page_info))
        response = await run_mcp_agent(
            prompt=user_prompt,
            system_prompt=system_prompt,
            allowed_servers=["heroui-react"],
            llm=self.model,
        )
        code = self._extract_generated_file(response)

        main_path = os.path.join(OUTPUT_DIR, "src", "main.tsx")
        os.makedirs(os.path.dirname(main_path), exist_ok=True)
        with open(main_path, "w", encoding="utf-8") as main_file:
            main_file.write(code + "\n")

        home_route = page_info[0]["route"] if page_info else "/"
        return {
            "message": f"Generated {main_path}.",
            "main_path": "src/main.tsx",
            "page_info": page_info,
            "route": home_route,
            "file_path": "src/main.tsx",
        }

    async def generate_single_page(self, state: dict, page_name: str, instruction: str = None) -> str:
        """Called by nodes.py to generate a single TSX page."""
        module_name = ProjectShellGenerator._module_name(page_name)
        page_path = os.path.join(OUTPUT_DIR, "src", "pages", f"{module_name}.tsx")

        design_sys = state.get("design_system_output", "")
        pages = state.get("page_design_output").pages if state.get("page_design_output") else []
        blueprint = next((p for p in pages if p.page_name == page_name), "")
        style = state.get("selected_style", "default")

        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(blueprint, design_sys, style, instruction)

        logger.info("Generating code for %s...", page_name)
        response = await run_mcp_agent(
            prompt=user_prompt,
            system_prompt=system_prompt,
            allowed_servers=[
                "heroui-react"
            ],
            llm=self.model
        )
        code = self._extract_tsx(response)

        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        with open(page_path, "w", encoding="utf-8") as page_file:
            page_file.write(code + "\n")
        return f"Generated {page_path}."

    async def repair_file(
        self,
        relative_path: str,
        original_code: str,
        errors: list,
        output_dir: str | None = None,
    ) -> str:
        """Repair a single file in the generated site using compile error context."""
        site_dir = output_dir or OUTPUT_DIR
        target_path = os.path.join(site_dir, relative_path.replace("/", os.sep))

        system_prompt = self.prompt_builder.build_repair_system_prompt()
        user_prompt = self.prompt_builder.build_repair_user_prompt(
            relative_path,
            original_code,
            errors,
        )

        logger.info("Repairing %s (%d errors)...", relative_path, len(errors))
        response = await run_mcp_agent(
            prompt=user_prompt,
            system_prompt=system_prompt,
            allowed_servers=["heroui-react"],
            llm=self.model,
        )
        code = self._extract_tsx(response)

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as page_file:
            page_file.write(code + "\n")
        return f"Repaired {relative_path}."

    @staticmethod
    def module_name_to_page_name(module_name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", " ", module_name).strip() or module_name

    async def generate_added_page(self, state: dict) -> dict:
        page_name = state["page_name"]
        message = await self.generate_single_page(state, page_name)
        module_name = ProjectShellGenerator._module_name(page_name)
        existing_pages = list(state["existing_page_design_output"].pages)
        shell_result = await self.generate_app_shell(
            state,
            existing_pages=existing_pages,
            instruction=f'Add navigation link for the new page "{page_name.strip()}".',
        )
        new_page = state["page_design_output"].pages[0]
        route = next(
            (item["route"] for item in shell_result["page_info"] if item["module"] == module_name),
            ProjectShellGenerator._route_path(page_name, len(existing_pages)),
        )
        return {
            "message": message,
            "module_name": module_name,
            "route": route,
            "file_path": f"src/pages/{module_name}.tsx",
        }

    def add_page_route(self, page_name: str) -> dict:
        """Deprecated: app shell is regenerated by generate_app_shell during add-page."""
        module_name = ProjectShellGenerator._module_name(page_name)
        route = ProjectShellGenerator._route_path(page_name, 1)
        return {
            "route": route,
            "file_path": f"src/pages/{module_name}.tsx",
            "main_path": "src/main.tsx",
        }

    async def install_and_start_dev_server(self) -> dict:
        """Called by nodes.py after all pages are generated."""
        return await self.server_manager.install_and_start(OUTPUT_DIR)


    def get_dev_server_status(self) -> dict:
        """Called by main.py to check if a dev server is already running."""
        return self.server_manager.get_status()
