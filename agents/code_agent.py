import asyncio
import json
import logging
import os
import shutil
import re
import subprocess
from pathlib import Path

try:
    from .llm import CODE_MODEL, invoke_text_model_async
except ImportError:
    from agents.llm import CODE_MODEL, invoke_text_model_async


logger = logging.getLogger(__name__)
PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(PACKAGE_ROOT, "frontend")
DEFAULT_GENERATED_PROJECT_DIR = os.path.join(PACKAGE_ROOT, ".generated", "latest")


SYSTEM_PROMPT = """
You are a senior frontend engineer building premium production-grade React + Tailwind websites, apps, tools, and utilities.

You write:
- clean React function components
- premium modern layouts
- motion-aware section structure
- coherent multi-page visual systems
- concise, readable JSX

Quality rules:
- Return valid JSX only
- No markdown
- No explanations
- Export a default component
- Build a polished visual hierarchy
- Match the supplied design system exactly
- Keep components self-contained
- If the request is for a calculator, editor, dashboard, game, or utility, build the actual usable interface as the primary screen
- Never recreate the surrounding generator app UI, chat panel, preview panel, style selector, or file/status counters
- You may use framer-motion, gsap, three, @react-three/fiber, @react-three/drei, and lenis when the request benefits from advanced motion or 3D
- Add animation-ready structure inspired by GSAP, Framer Motion, and React Three Fiber patterns
- If the concept strongly benefits from advanced animation, introduce it carefully and only when the component still remains buildable
- Avoid placeholder lorem ipsum
- Keep sections purposeful and visually distinct
- Do not reference undeclared local asset files
- Do not use /assets/*, /public/*, root-relative media files, or local .svg/.png/.jpg/.mp4/.webm paths
- Use CSS gradients, inline SVG, and pure JSX/Tailwind structure instead of file-based media
- Do not use emoji glyphs or non-ASCII decorative symbols; use inline SVG or text labels instead
"""


def _strip_code_fences(code: str) -> str:
    return re.sub(r"```(?:jsx|javascript|js)?|```", "", code).strip()


def _validate_jsx_syntax(path: str, code: str) -> None:
    parser_dir = FRONTEND_DIR
    if not os.path.isdir(os.path.join(parser_dir, "node_modules", "@babel", "parser")):
        logger.warning("Skipping JSX syntax validation; @babel/parser is not installed")
        return

    parser_script = """
const parser = require("@babel/parser");
let source = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => source += chunk);
process.stdin.on("end", () => {
  try {
    parser.parse(source, {
      sourceType: "module",
      plugins: ["jsx"],
      errorRecovery: false
    });
  } catch (error) {
    console.error(`${error.message}`);
    process.exit(1);
  }
});
"""

    result = subprocess.run(
        ["node", "-e", parser_script],
        input=code,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=parser_dir,
        timeout=20,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown JSX syntax error"
        raise ValueError(f"{path}: {message}")


def _component_name(page_name: str) -> str:
    return "".join(word.capitalize() for word in page_name.split("_")) or "Page"


def _derive_brand_label(prompt: str) -> str:
    stopwords = {
        "a",
        "an",
        "and",
        "app",
        "build",
        "create",
        "design",
        "for",
        "generate",
        "landing",
        "page",
        "premium",
        "site",
        "startup",
        "style",
        "the",
        "website",
        "with",
    }
    tokens = re.findall(r"[A-Za-z0-9]+", prompt)
    filtered = [token for token in tokens if token.lower() not in stopwords]

    if not filtered:
        return "Studio"

    selected = filtered[:2]
    normalized = []
    for token in selected:
        if token.lower() == "ai":
            normalized.append("AI")
        else:
            normalized.append(token.capitalize())
    return " ".join(normalized)


def _normalize_page_specs(state: dict) -> list[dict]:
    page_map: dict[str, dict] = {}
    image_map = state.get("images", {}).get("pages", {})

    for page in state.get("pages", {}).get("pages", []):
        page_name = page.get("name")
        if not page_name:
            continue
        page_map[page_name] = {
            "name": page_name,
            "route": page.get("route", "/"),
            "type": page.get("type", "marketing"),
            "goal": page.get("goal", ""),
            "sections": page.get("sections", []),
            "image_prompt": page.get("image_prompt", ""),
            "requires_generated_visual": page.get("requires_generated_visual", False),
            "ui_sections": [],
            "images": image_map.get(page_name, {}),
        }

    for page in state.get("ui", {}).get("pages", []):
        page_name = page.get("name")
        if not page_name:
            continue

        if page_name not in page_map:
            page_map[page_name] = {
                "name": page_name,
                "route": page.get("route", "/"),
                "type": "marketing",
                "goal": "",
                "sections": [],
                "image_prompt": "",
                "requires_generated_visual": False,
                "ui_sections": page.get("ui_sections", []),
                "images": image_map.get(page_name, {}),
            }
        else:
            page_map[page_name]["ui_sections"] = page.get("ui_sections", [])

    return list(page_map.values())


def _build_app_shell(page_specs: list[dict], design: dict, brand_label: str) -> str:
    imports = []
    route_entries = []
    nav_links = []

    for page in page_specs:
        component_name = _component_name(page["name"])
        route = page.get("route", "/")
        label = page["name"].replace("_", " ").title()
        imports.append(f'import {component_name} from "./pages/{component_name}";')
        route_entries.append(f'  "{route}": {component_name},')
        nav_links.append(
            "{ route: "
            + json.dumps(route)
            + f', label: "{label}"'
            + " }"
        )

    background = design.get("palette", {}).get("background", "#020617")
    text = design.get("palette", {}).get("text", "#f8fafc")
    surface = design.get("palette", {}).get("surface", "rgba(15, 23, 42, 0.72)")
    accent = design.get("palette", {}).get("accent", "#d3ff72")

    return f"""
import {{ useEffect, useState }} from "react";
{chr(10).join(imports)}

const routes = {{
{chr(10).join(route_entries)}
}};

const navigation = [{", ".join(nav_links)}];

function getCurrentRoute() {{
  const hash = window.location.hash.replace(/^#/, "") || "/";
  return routes[hash] ? hash : "/";
}}

export default function App() {{
  const [route, setRoute] = useState(getCurrentRoute());

  useEffect(() => {{
    const handleHashChange = () => setRoute(getCurrentRoute());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }}, []);

  const ActivePage = routes[route] || routes["/"];

  return (
    <div className="min-h-screen" style={{{{ background: "{background}", color: "{text}" }}}}>
      {{navigation.length > 1 && (
        <header
          className="sticky top-0 z-50 border-b px-5 py-3 backdrop-blur-xl"
          style={{{{
            background: "{surface}",
            borderColor: "rgba(255,255,255,0.12)"
          }}}}
        >
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-5">
            <button
              type="button"
              onClick={{() => {{
                window.location.hash = "/";
                setRoute("/");
              }}}}
              className="text-sm font-semibold uppercase tracking-[0.35em]"
              style={{{{ color: "{accent}" }}}}
            >
              {brand_label}
            </button>
            <nav className="flex flex-wrap items-center justify-end gap-2 text-sm">
              {{navigation.map((item) => (
                <button
                  type="button"
                  key={{item.route}}
                  onClick={{() => {{
                    window.location.hash = item.route;
                    setRoute(item.route);
                  }}}}
                  className={{[
                    "rounded-full px-4 py-2 transition",
                    route === item.route
                      ? "bg-white text-slate-950"
                      : "text-white/75 hover:bg-white/10 hover:text-white"
                  ].join(" ")}}
                >
                  {{item.label}}
                </button>
              ))}}
            </nav>
          </div>
        </header>
      )}}
      <ActivePage />
    </div>
  );
}}
""".strip()


def _build_main_file() -> str:
    return """
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""".strip()


def _build_index_html(site_title: str) -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>__SITE_TITLE__</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""".replace("__SITE_TITLE__", site_title).strip()


def _build_package_json() -> str:
    return json.dumps(
        {
            "name": "generated-website",
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
            },
            "dependencies": {
                "@vitejs/plugin-react": "latest",
                "@react-three/drei": "latest",
                "@react-three/fiber": "latest",
                "framer-motion": "latest",
                "gsap": "latest",
                "lenis": "latest",
                "vite": "latest",
                "typescript": "latest",
                "react": "latest",
                "react-dom": "latest",
                "three": "latest",
                "tailwindcss": "latest",
                "@tailwindcss/vite": "latest",
            },
            "devDependencies": {},
        },
        indent=2,
    )


def _build_styles_file(design: dict) -> str:
    background = design.get("palette", {}).get("background", "#020617")
    text = design.get("palette", {}).get("text", "#f8fafc")
    primary = design.get("palette", {}).get("primary", "#22d3ee")
    accent = design.get("palette", {}).get("accent", "#d3ff72")

    return f"""
@import "tailwindcss";

:root {{
  color: {text};
  background: {background};
  --color-primary: {primary};
  --color-accent: {accent};
}}

html,
body,
#root {{
  min-height: 100%;
  margin: 0;
}}

body {{
  background: {background};
}}

* {{
  box-sizing: border-box;
}}
""".strip()


def _build_vite_config() -> str:
    return """
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1"
  }
});
""".strip()


def _package_project_files(files: dict[str, str], design: dict, site_title: str) -> dict[str, str]:
    packaged: dict[str, str] = {
        "package.json": _build_package_json(),
        "index.html": _build_index_html(site_title=site_title),
        "vite.config.js": _build_vite_config(),
        "src/main.jsx": _build_main_file(),
        "src/styles.css": _build_styles_file(design),
    }

    for name, code in files.items():
        if name == "App.jsx":
            packaged["src/App.jsx"] = code
        else:
            packaged[f"src/pages/{name}"] = code

    return packaged


def _generated_project_validation_enabled() -> bool:
    return os.getenv("VALIDATE_GENERATED_PROJECT", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _generated_project_repair_attempts() -> int:
    return max(0, int(os.getenv("GENERATED_PROJECT_REPAIR_ATTEMPTS", "1")))


def _generated_project_dir() -> Path:
    configured = os.getenv("GENERATED_PROJECT_DIR", DEFAULT_GENERATED_PROJECT_DIR)
    path = Path(configured).resolve()
    allowed_roots = [Path(PACKAGE_ROOT).resolve(), Path(r"C:\tmp").resolve()]

    if not any(allowed_root in [path, *path.parents] for allowed_root in allowed_roots):
        raise ValueError(
            "GENERATED_PROJECT_DIR must stay inside one of "
            + ", ".join(str(root) for root in allowed_roots)
            + f"; got {path}"
        )

    return path


def _write_generated_project(files: dict[str, str], target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    for relative_path, content in files.items():
        destination = (target_dir / relative_path).resolve()
        if target_dir not in [destination, *destination.parents]:
            raise ValueError(f"Refusing to write outside generated project: {relative_path}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def _run_project_command(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )


def _format_command_output(result: subprocess.CompletedProcess[str], limit: int = 12000) -> str:
    output = "\n".join(
        part
        for part in [
            f"command: {' '.join(result.args) if isinstance(result.args, list) else result.args}",
            f"exit_code: {result.returncode}",
            result.stdout.strip(),
            result.stderr.strip(),
        ]
        if part
    )
    return output[-limit:]


def _validate_generated_project_build(files: dict[str, str]) -> tuple[bool, str]:
    target_dir = _generated_project_dir()
    print(f"[validate] writing generated project: {target_dir}", flush=True)
    _write_generated_project(files=files, target_dir=target_dir)

    install_timeout = int(os.getenv("GENERATED_PROJECT_INSTALL_TIMEOUT_SECONDS", "180"))
    build_timeout = int(os.getenv("GENERATED_PROJECT_BUILD_TIMEOUT_SECONDS", "120"))
    npm_command = os.getenv("NPM_COMMAND", "npm.cmd")

    print("[validate] npm install: started", flush=True)
    install_result = _run_project_command(
        [npm_command, "install", "--silent", "--no-audit", "--no-fund"],
        cwd=target_dir,
        timeout_seconds=install_timeout,
    )
    if install_result.returncode != 0:
        return False, _format_command_output(install_result)
    print("[validate] npm install: completed", flush=True)

    print("[validate] npm run build: started", flush=True)
    build_result = _run_project_command(
        [npm_command, "run", "build"],
        cwd=target_dir,
        timeout_seconds=build_timeout,
    )
    if build_result.returncode != 0:
        return False, _format_command_output(build_result)
    print("[validate] npm run build: completed", flush=True)

    return True, _format_command_output(build_result, limit=4000)


def _select_repair_files(files: dict[str, str], build_log: str) -> dict[str, str]:
    candidates = {
        path: content
        for path, content in files.items()
        if path.endswith((".jsx", ".js", ".css", ".html", ".json"))
    }

    mentioned = {
        path: content
        for path, content in candidates.items()
        if path in build_log or path.replace("/", "\\") in build_log
    }

    if mentioned:
        return mentioned

    fallback_paths = {"src/App.jsx", "src/main.jsx", "src/styles.css", "vite.config.js", "package.json"}
    return {
        path: content
        for path, content in candidates.items()
        if path in fallback_paths or path.startswith("src/pages/")
    }


async def _repair_generated_project_files(
    files: dict[str, str],
    build_log: str,
    prompt: str,
    selected_style: str,
) -> dict[str, str]:
    repair_files = _select_repair_files(files=files, build_log=build_log)

    repair_prompt = f"""
User request:
{prompt}

Selected style:
{selected_style}

The generated Vite React project failed validation.

Build log:
{build_log}

Files to repair:
{json.dumps(repair_files, indent=2)}

Return a JSON object mapping file paths to full corrected file contents.
Only include files that need changes.
Do not use markdown fences.
Keep the existing Vite React project structure.
Do not remove required pages or routes unless the build log proves they are invalid.
"""

    response = await invoke_text_model_async(
        prompt=repair_prompt,
        system_prompt=(
            "You are a senior React build repair engineer. "
            "Return valid JSON only: {\"path\": \"full file content\"}."
        ),
        model_name=CODE_MODEL,
        temperature=0.2,
    )

    cleaned = _strip_code_fences(response)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("Repair model did not return a JSON object")

    repaired_payload = json.loads(match.group(0))
    if not isinstance(repaired_payload, dict):
        raise ValueError("Repair model returned a non-object JSON payload")

    repaired_files = dict(files)
    for path, content in repaired_payload.items():
        if not isinstance(path, str) or not isinstance(content, str):
            continue
        if path not in files:
            logger.warning("Repair returned unknown file path: %s", path)
            continue
        repaired_files[path] = _strip_code_fences(content)

    return repaired_files


def _validate_and_repair_generated_project(
    files: dict[str, str],
    prompt: str,
    selected_style: str,
) -> dict[str, str]:
    if not _generated_project_validation_enabled():
        return files

    attempts = _generated_project_repair_attempts()
    current_files = files
    last_log = ""

    for attempt in range(0, attempts + 1):
        is_valid, build_log = _validate_generated_project_build(current_files)
        if is_valid:
            print("[validate] generated project build passed", flush=True)
            return current_files

        last_log = build_log
        print(f"[validate] generated project build failed on attempt {attempt + 1}", flush=True)

        if attempt >= attempts:
            break

        print(f"[repair] generated project repair attempt {attempt + 1}: started", flush=True)
        current_files = asyncio.run(
            _repair_generated_project_files(
                files=current_files,
                build_log=build_log,
                prompt=prompt,
                selected_style=selected_style,
            )
        )
        print(f"[repair] generated project repair attempt {attempt + 1}: completed", flush=True)

    raise RuntimeError("Generated project build validation failed:\n" + last_log)


async def _generate_single_page(
    prompt: str,
    selected_style: str,
    design: dict,
    inspiration_data: dict,
    page: dict,
    site_context: list[dict],
) -> tuple[str, str]:
    component_name = _component_name(page.get("name", "page"))
    print(f"[code] {component_name}: generation started", flush=True)

    code_prompt = f"""
User Request:
{prompt}

Selected Design Style:
{selected_style}

Research Context:
{json.dumps({
    "summary": inspiration_data.get("research_summary", ""),
    "references": inspiration_data.get("references", [])[:4],
    "queries": inspiration_data.get("queries", []),
}, indent=2)}

Shared Design System:
{json.dumps(design, indent=2)}

Current Page:
{json.dumps(page, indent=2)}

Other Site Pages:
{json.dumps(site_context, indent=2)}

Generate a premium React + Tailwind component for this page.

Implementation requirements:
- Component name must be {component_name}
- Export default component
- Use the supplied ui_sections exactly and in order
- Respect the original user request as the primary product requirement
- If this page type is "tool", "utility", "dashboard", "game", or "app", make it functional and interactive with React state where appropriate
- For calculator requests, implement working buttons, numeric input behavior, common operations, result display, clear/delete behavior, and calculation history
- Do not build or imitate a website-generator interface
- For multi-page websites, include clear page-level navigation links or calls to action that use the supplied routes
- When advanced motion or 3D is useful, import and use framer-motion, gsap, three, @react-three/fiber, @react-three/drei, or lenis directly
- This generated project uses Vite React, not Next.js; implement SEO-friendly semantic React structure instead of Next-specific APIs
- Make the design visually premium, modern, and polished
- Create strong motion-ready composition inspired by GSAP, Framer Motion, and React Three Fiber
- Use tasteful gradients, layered backgrounds, glass, grids, cards, and strong typography when appropriate
- Do not require external assets
- Do not reference /assets/*, /public/*, or root-relative media files
- Do not depend on local svg/image/video files
- Use the provided remote image URLs when a hero, banner, showcase, or product visual improves the page
- Never invent your own image URLs; only use the URLs present in the Current Page payload
- If Current Page requires_generated_visual is true, you must visibly use at least one provided generated image URL in the rendered JSX
- Prefer large editorial image treatments for premium marketing pages rather than small decorative thumbnails
- Keep the component self-contained
- Ensure the page feels connected to the other site pages through tone and navigation cues
- Keep JSX valid and production-lean
- Before returning, mentally parse the file and ensure every string, array, object, function, JSX tag, and parenthesis is closed
- Do not place component declarations inside string literals, object string values, array text values, FAQ answers, or copy blocks
- Do not use emoji glyphs or non-ASCII decorative symbols such as lightning, sparkles, arrows, bullets, or dingbats
"""

    last_error: Exception | None = None
    code = ""

    for attempt in range(1, 3):
        prompt_for_attempt = code_prompt
        if last_error is not None:
            prompt_for_attempt = f"""
The previous generated file for {component_name} was invalid.

Syntax/validation error:
{last_error}

Previous invalid code:
{code}

Return the corrected full React component file only.
No markdown. No explanations. Ensure valid JSX syntax.
"""

        response = await invoke_text_model_async(
            prompt=prompt_for_attempt,
            system_prompt=SYSTEM_PROMPT,
            model_name=CODE_MODEL,
            temperature=0.5 if attempt > 1 else 0.7,
        )

        code = _strip_code_fences(response)
        try:
            if "export default function" not in code and "export default" not in code:
                raise ValueError(f"Model did not return a default export for {component_name}")
            _validate_jsx_syntax(f"{component_name}.jsx", code)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            print(f"[code] {component_name}: validation failed on attempt {attempt} ({exc})", flush=True)

    if last_error is not None:
        raise ValueError(f"Generated invalid JSX for {component_name}: {last_error}")

    print(f"[code] {component_name}: generation completed", flush=True)
    return f"{component_name}.jsx", code


def generate_code(state: dict) -> dict:
    prompt = state.get("prompt", "")
    selected_style = str(state.get("selected_style", "")).strip()
    if not selected_style:
        raise ValueError("selected_style is required")
    design = state.get("design", {})
    inspiration_data = state.get("inspiration_data", {})
    page_specs = _normalize_page_specs(state)
    brand_label = _derive_brand_label(prompt)

    if not page_specs:
        raise ValueError("No UI pages generated")

    async def _generate_all_pages() -> dict[str, str]:
        print(f"[code] parallel generation: {len(page_specs)} page tasks", flush=True)
        tasks = {
            page["name"]: _generate_single_page(
                prompt=prompt,
                selected_style=selected_style,
                design=design,
                inspiration_data=inspiration_data,
                page=page,
                site_context=[
                    {
                        "name": sibling["name"],
                        "route": sibling.get("route", "/"),
                        "type": sibling.get("type", "marketing"),
                    }
                    for sibling in page_specs
                    if sibling["name"] != page["name"]
                ],
            )
            for page in page_specs
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        files: dict[str, str] = {}
        failures: list[str] = []

        for page_name, result in zip(tasks.keys(), results):
            file_name = f"{_component_name(page_name)}.jsx"

            if isinstance(result, Exception):
                print(f"[code] {file_name}: generation failed", flush=True)
                logger.error(
                    "Page generation failed for %s: %s",
                    page_name,
                    result,
                    exc_info=result,
                )
                failures.append(f"{page_name}: {result}")
                continue

            generated_file_name, code = result
            files[generated_file_name] = code

        if failures:
            raise RuntimeError(
                "Page code generation failed for: " + "; ".join(failures)
            )

        return files

    files = asyncio.run(_generate_all_pages())
    print("[code] app shell: building", flush=True)
    files["App.jsx"] = _build_app_shell(
        page_specs=page_specs,
        design=design,
        brand_label=brand_label,
    )
    print("[code] app shell: completed", flush=True)
    print("[code] project package: building", flush=True)
    files = _package_project_files(files=files, design=design, site_title=brand_label)
    print(f"[code] project package: completed ({len(files)} files)", flush=True)
    files = _validate_and_repair_generated_project(
        files=files,
        prompt=prompt,
        selected_style=selected_style,
    )

    return {"files": files}
