from schema.code import CodeGenerationInput
from agents.llm import gemini_flash_llm, mcp_code_llm
from agents.resilient_llm import resilient_ainvoke
from mcp_tools.initialize_mcps import run_mcp_agent
from langchain_core.messages import HumanMessage, SystemMessage
import os
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)

SYSTEM_PROMPT = """
You are an expert frontend engineer.

Your task is to generate a React + TailwindCSS page based on a wireframe blueprint.
You are generating code BEFORE visual assets have been created.
Use placeholders like `https://placehold.co/600x400` for images, and standard SVG shapes for icons.

Use:
- User Prompt
- Design System Output
- Page Blueprint
- Context7 MCP for current React, TypeScript, TailwindCSS, GSAP, and React Router usage when you need library guidance.
- Filesystem MCP for all project file writes.

Rules:
- Create reusable React components.
- Use TailwindCSS for styling.
- Use GSAP for animations (ScrollTrigger, etc.).
- Generate production-ready code.
- Do not create generic filler pages. Implement the sections and components from the PAGE BLUEPRINT.
- Write files only inside the output directory provided.
- Write source files under src.
- You must write a complete React component for the requested page.
- For `write_file`, `path` must be a string and `content` must be one plain string containing the complete file text.
- Never send `content` as a JSON object, array, map, or nested structure. Never repeat an invalid `write_file` call.
- Do not use `read_text_file`: it is incompatible with this filesystem server. Use `read_multiple_files` to inspect existing source files.

Return a concise summary of the files written.
Return final answer immediately with a concise list of files written.
Use the filesystem tool to create each file.
"""

STYLE_GUIDANCE = {
    "glassmorphism":
        "Use Apple/Vercel/Linear style aesthetics. Use glassmorphism "
        "(`backdrop-blur-xl bg-white/5 border border-white/10`), glowing "
        "radial gradients behind sections, tight typography leading, and "
        "high-contrast text.",

    "neo_brutalism":
        "Use hard black borders (`border-2 border-black`), solid bold colors "
        "(bright yellow, red, blue), hard shadows "
        "(`shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]`), and uppercase headings. "
        "No gradients, no blur.",

    "minimalism":
        "Use excessive whitespace, zero borders, very light gray or pure "
        "white backgrounds, sparse typography, and extremely subtle hover "
        "states. No gradients, no glassmorphism.",

    "liquid_glass":
        "Use visionOS-style liquid blur: layered translucent surfaces "
        "(`backdrop-blur-2xl bg-white/10`), luminous soft-edged highlights, "
        "rounded-full or very large radii, and subtle refractive gradient "
        "borders. Motion should feel fluid and buoyant, not sharp.",

    "claymorphism":
        "Use soft, puffy surfaces with large border-radius (`rounded-3xl`), "
        "dual soft shadows (one light, one dark) to fake extruded depth "
        "(`shadow-[6px_6px_16px_rgba(0,0,0,0.15),-6px_-6px_16px_rgba(255,255,255,0.7)]`), "
        "pastel or muted colors, and playful rounded typography.",

    "skeuomorphism":
        "Use realistic physical metaphors: subtle gradients simulating "
        "material (brushed metal, paper, leather textures via layered "
        "shadows), tactile-looking buttons with pressed/raised states, "
        "drop shadows implying real light sources, and skeuomorphic icons.",
}

class PageCodeAgent:
    def __init__(self):
        self.model = gemini_flash_llm()
        self.mcp_model = mcp_code_llm()

    def _module_name(self, name: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", name)
        if not words:
            return "Page"
        return "".join(word[:1].upper() + word[1:] for word in words)

    def _route_path(self, page_name: str, index: int) -> str:
        if index == 0:
            return "/"
        words = re.findall(r"[A-Za-z0-9]+", page_name.lower())
        return "/" + "-".join(words)

    @staticmethod
    def _response_text(response) -> str:
        """Normalize ChatNVIDIA content before saving a generated TSX file."""
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts)
        return str(content)

    @classmethod
    def _extract_tsx(cls, response) -> str:
        text = cls._response_text(response).strip()
        fenced = re.search(r"```(?:tsx|typescript|jsx|javascript)?\\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        code = (fenced.group(1) if fenced else text).strip()
        if "export default" not in code:
            raise ValueError("The code model did not return a complete React page component.")
        return code

    def _write_tailwind_config(self, design_output) -> str:
        if not design_output:
            return ""
        
        config = f"""
/** @type {{import('tailwindcss').Config}} */
export default {{
  content: [
    "./index.html",
    "./src/**/*.{{js,ts,jsx,tsx}}",
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: '{design_output.colors.primary}',
        secondary: '{design_output.colors.secondary}',
        accent: '{design_output.colors.accent}',
        background: '{design_output.colors.background}',
        surface: '{design_output.colors.surface}',
        success: '{design_output.colors.success}',
        warning: '{design_output.colors.warning}',
        error: '{design_output.colors.error}',
      }},
      fontFamily: {{
        heading: ['{design_output.typography.heading_font}', 'sans-serif'],
        body: ['{design_output.typography.body_font}', 'sans-serif'],
      }},
      spacing: {{
        'xxs': '{design_output.spacing.xxs}',
        'xs': '{design_output.spacing.xs}',
        'sm': '{design_output.spacing.sm}',
        'md': '{design_output.spacing.md}',
        'lg': '{design_output.spacing.lg}',
        'xl': '{design_output.spacing.xl}',
        'xxl': '{design_output.spacing.xxl}',
      }},
      borderRadius: {{
        'sm': '{design_output.radius.small}',
        'md': '{design_output.radius.medium}',
        'lg': '{design_output.radius.large}',
        'pill': '{design_output.radius.pill}',
      }},
      boxShadow: {{
        'sm': '{design_output.shadows.small}',
        'md': '{design_output.shadows.medium}',
        'lg': '{design_output.shadows.large}',
      }},
    }},
  }},
  plugins: [],
}}
"""
        filepath = os.path.join(OUTPUT_DIR, "tailwind.config.js")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(config.strip())
        return filepath

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

    def _write_index_css(self, design_output=None) -> str:
        background = "#f8fafc"
        text = "#0f172a"
        if design_output:
            background = getattr(design_output.colors, "background", background)
            text = getattr(design_output.colors, "surface", text)
            if self._is_dark_hex_color(background):
                text = getattr(design_output.colors, "dark_surface", "#f7f2e8")
        css = f"""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{ font-family: Inter, system-ui, sans-serif; color: {text}; background: {background}; }}
* {{ box-sizing: border-box; }}
html, body, #root {{ min-height: 100%; margin: 0; }}
body {{ min-width: 320px; }}
"""
        filepath = os.path.join(OUTPUT_DIR, "src", "index.css")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(css)
        return filepath

    def _create_project_shell(self, state: dict) -> str:
        """Create stable shared files without spending an MCP tool-call turn."""
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

        pages = state["page_design_output"].pages
        page_info = [
            {
                "module": self._module_name(page.page_name),
                "route": self._route_path(index=index, page_name=page.page_name),
                "label": page.page_name,
            }
            for index, page in enumerate(pages)
        ]
        imports = "\n".join(
            f'import {item["module"]} from "./pages/{item["module"]}";'
            for item in page_info
        )
        routes = "\n".join(
            f'        <Route path={json.dumps(item["route"])} element={{<{item["module"]} />}} />'
            for item in page_info
        )

        package = {
            "name": "generated-website",
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {"dev": "vite", "build": "tsc -b", "preview": "vite preview"},
            "dependencies": {
                "@gsap/react": "^2.1.1",
                "framer-motion": "^11.11.17",
                "gsap": "^3.12.5",
                "lenis": "^1.1.18",
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "react-router-dom": "^7.1.1",
            },
            "devDependencies": {
                "@types/node": "^22.10.2",
                "@types/react": "^18.3.12",
                "@types/react-dom": "^18.3.1",
                "@vitejs/plugin-react": "^4.3.4",
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.49",
                "tailwindcss": "^3.4.17",
                "typescript": "^5.7.2",
                "vite": "^6.0.5",
            },
        }

        files = {
            "package.json": json.dumps(package, indent=2) + "\n",
            "index.html": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Generated Website</title>
  </head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
""",
            "tsconfig.json": '{"files": [], "references": [{"path":"./tsconfig.app.json"},{"path":"./tsconfig.node.json"}]}\n',
            "tsconfig.app.json": """{
  "compilerOptions": {"target":"ES2020","useDefineForClassFields":true,"lib":["ES2020","DOM","DOM.Iterable"],"skipLibCheck":true,"esModuleInterop":true,"allowSyntheticDefaultImports":true,"strict":true,"module":"ESNext","moduleResolution":"Bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx"},
  "include": ["src"]
}
""",
            "tsconfig.node.json": """{
  "compilerOptions": {"composite":true,"skipLibCheck":true,"module":"ESNext","moduleResolution":"Bundler","types":["node"]},
  "include": ["vite.config.ts"]
}
""",
            "vite.config.ts": """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig({ plugins:[react()], resolve:{ alias:{"@":path.resolve(__dirname,"src")} } });
""",
            "src/main.tsx": f'''import {{ StrictMode }} from "react";
import {{ createRoot }} from "react-dom/client";
import {{ BrowserRouter, Route, Routes, Navigate }} from "react-router-dom";
import "./index.css";
{imports}

const App = () => (
  <div className="min-h-screen bg-slate-50 text-slate-900">
    <main className="p-4">
      <Routes>
{routes}
        <Route path="*" element={{<Navigate to="/" replace />}} />
      </Routes>
    </main>
  </div>
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
''',
            "src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;
:root { font-family: Inter, system-ui, sans-serif; color: #0f172a; background: #f8fafc; }
* { box-sizing: border-box; }
html, body, #root { min-height: 100%; margin: 0; }
""",
            "src/components/Button.tsx": """import type { ButtonHTMLAttributes } from "react";

export function Button({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded-full px-5 py-3 font-medium transition hover:opacity-80 ${className}`}
      {...props}
    />
  );
}

export default Button;
""",
            "src/components/Card.tsx": """import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border border-white/10 bg-white/5 p-6 ${className}`}
      {...props}
    />
  );
}

export default Card;
""",
            "src/components/index.tsx": """export { Button } from "./Button";
export { Card } from "./Card";
""",
        }
        for relative_path, content in files.items():
            filepath = os.path.join(OUTPUT_DIR, relative_path)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(content)

        return f"Created deterministic project shell for {len(page_info)} pages."

    async def generate_project_shell(self, state: dict) -> str:
        return self._create_project_shell(state)

    async def _generate_project_shell_with_mcp(self, state: dict) -> str:
        pages_summary = [
            {
                "page_name": page.page_name,
                "module": self._module_name(page.page_name),
                "route": self._route_path(index=index, page_name=page.page_name),
                "label": page.page_name,
                "goal": page.page_goal,
            }
            for index, page in enumerate(state["page_design_output"].pages)
        ]

        design_output = state.get("design_system_output")
        if design_output:
            self._write_tailwind_config(design_output)
            self._write_index_css(design_output)
        else:
            self._write_index_css()

        os.makedirs(os.path.join(OUTPUT_DIR, "src", "components"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "src", "pages"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "src", "hooks"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "src", "lib"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "src", "assets"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "public"), exist_ok=True)

        package = {
            "name": "generated-website",
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {"dev": "vite", "build": "tsc -b && vite build", "preview": "vite preview"},
            "dependencies": {
                "@gsap/react": "^2.1.1",
                "framer-motion": "^11.11.17",
                "gsap": "^3.12.5",
                "lenis": "^1.1.18",
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "react-router-dom": "^7.1.1",
            },
            "devDependencies": {
                "@types/react": "^18.3.12",
                "@types/react-dom": "^18.3.1",
                "@vitejs/plugin-react": "^4.3.4",
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.49",
                "tailwindcss": "^3.4.17",
                "typescript": "^5.7.2",
                "vite": "^6.0.5",
            },
        }

        imports = "\n".join(
            f'import {page["module"]} from "./pages/{page["module"]}";'
            for page in pages_summary
        )
        routes = "\n".join(
            f'          <Route path={json.dumps(page["route"])} element={{<{page["module"]} />}} />'
            for page in pages_summary
        )

        files = {
            "package.json": json.dumps(package, indent=2) + "\n",
            "index.html": """<!doctype html>
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
""",
            "tsconfig.json": """{
  "files": [],
  "references": [{ "path": "./tsconfig.app.json" }, { "path": "./tsconfig.node.json" }]
}
""",
            "tsconfig.app.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
""",
            "tsconfig.node.json": """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
""",
            "vite.config.ts": """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
});
""",
            "src/main.tsx": f'''import {{ StrictMode }} from "react";
import {{ createRoot }} from "react-dom/client";
import {{ BrowserRouter, Route, Routes, Navigate }} from "react-router-dom";
import "./index.css";
{imports}

const App = () => (
  <div className="min-h-screen bg-slate-50 text-slate-900">
    <main className="p-4">
      <Routes>
{routes}
        <Route path="*" element={{<Navigate to="/" replace />}} />
      </Routes>
    </main>
  </div>
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
''',
            "src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;

:root { font-family: Inter, system-ui, sans-serif; color: #0f172a; background: #f8fafc; }
* { box-sizing: border-box; }
html, body, #root { min-height: 100%; margin: 0; }
body { min-width: 320px; }
""",
            "src/components/Button.tsx": """import type { ButtonHTMLAttributes } from "react";

export function Button({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded-full px-5 py-3 font-medium transition hover:opacity-80 ${className}`}
      {...props}
    />
  );
}

export default Button;
""",
            "src/components/Card.tsx": """import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border border-white/10 bg-white/5 p-6 ${className}`}
      {...props}
    />
  );
}

export default Card;
""",
            "src/components/index.tsx": """export { Button } from "./Button";
export { Card } from "./Card";
""",
        }

        for relative_path, content in files.items():
            filepath = os.path.join(OUTPUT_DIR, relative_path)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(content)

        return f"Created deterministic project shell for {len(pages_summary)} pages."

    async def generate_single_page(self, state: dict, page_name: str, instruction: str = None) -> str:
        page = next((p for p in state["page_design_output"].pages if p.page_name == page_name), None)
        if not page:
            raise ValueError(f"Page {page_name} not found in state.")
            
        module_name = self._module_name(page.page_name)
        page_path = os.path.join(OUTPUT_DIR, "src", "pages", f"{module_name}.tsx")

        style_key = state.get("selected_style", "glassmorphism")
        style_instruction = STYLE_GUIDANCE.get(style_key, STYLE_GUIDANCE["glassmorphism"])

        design_output = state.get("design_system_output")
        design_system_text = ""
        if design_output:
            design_system_text = f"""
Design system:
Colors:
{design_output.colors.model_dump_json(indent=2)}
Typography:
{design_output.typography.model_dump_json(indent=2)}
Spacing:
{design_output.spacing.model_dump_json(indent=2)}
Radius:
{design_output.radius.model_dump_json(indent=2)}
Shadows:
{design_output.shadows.model_dump_json(indent=2)}
Component guidelines:
{[c.model_dump_json(indent=2) for c in design_output.component_guidelines]}
"""

        pages = state["page_design_output"].pages
        site_navigation = "\n".join(
            f"- {self._route_path(index=index, page_name=page.page_name)}: {page.page_name}"
            for index, page in enumerate(pages)
        )

        prompt = f"""
Generate exactly one complete React TSX page component.

File path: {page_path}
Default export name: {module_name}

User request:
{state["user_prompt"]}

Page blueprint:
{page.model_dump_json(indent=2)}

Site navigation:
{site_navigation}

If the site includes more than one page, include page-to-page navigation inside this page using react-router-dom. You can use:
- <Link to="/other-page">Go to Other Page</Link>
- or useNavigate() to navigate programmatically on button click.

{design_system_text}
Style guidance ({style_key}):
{style_instruction}
"""

        if instruction:
            prompt += f"\n\nUSER EDIT INSTRUCTION:\n{instruction}\nModify the page specifically to address this instruction."

        prompt += f"""
Requirements:
- Return only the complete TSX source code. Do not inspect files, explain your work, or use markdown fences.
- Use the design system colors, typography, spacing, shadows, and component guidelines to determine whether the page should use a light or dark theme.
- Do not force a dark background. Choose light or dark styling based on the user prompt and design system.
- Import ONLY from: React, react-router-dom, gsap, framer-motion, and existing components from '../components/Button', '../components/Card'
- You can import Button and Card like this:
  import Button from '../components/Button';
  import Card from '../components/Card';
  OR use named imports:
  import {{ Button }} from '../components/Button';
  import {{ Card }} from '../components/Card';
- For other custom components you need, create them inline within this file as reusable React components.
- Use placehold.co URLs for all images since assets are not generated yet.
- IMPORTANT: Tag EVERY placeholder <img> element with `data-asset-id="unique_id"` and `data-asset-prompt="Highly detailed description of what the generated image should be, matching the design theme"`. Example:
  <img src="https://placehold.co/800x600" data-asset-id="{module_name.lower()}_hero_bg" data-asset-prompt="Premium dark minimalist dashboard background, tech aesthetic, 4k" className="..." />
- If this page is part of a multi-page website, include a Websites navigation tab or page-to-page links/buttons so users can move between generated pages.
- Implement every section from PAGE BLUEPRINT in order.
- Use GSAP for page animations (scroll reveals, card reveals, hover effects, section transitions).
- Use the heroui-react MCP server only for creating reusable React components and component implementation details.
- Do not treat the heroui-react MCP server as a full-page generator. The page structure should be composed locally from components that the MCP helps implement.
- Do not include image-dependent animations (like parallax) for placeholder images yet. Parallax will be injected later.
- Only include abstract background animations (like canvas particle nets or gradient blobs) if the selected style explicitly calls for them.
- Export default {module_name}.
- Do not rely on a Tailwind configuration file. Use standard Tailwind utility classes only.
"""

        code = None

        try:
            response_text = await run_mcp_agent(
                prompt=prompt,
                allowed_servers=["heroui-react"],
                system_prompt="You are a senior frontend engineer. Return only valid, complete TSX source code.",
                llm=self.model,
                max_steps=20,
            )
            code = self._extract_tsx(response_text)
            logger.info("Generated page source via heroui-react MCP: %s", page_path)
        except Exception as mcp_exc:
            logger.warning(
                "heroui-react MCP generation failed: %s. Falling back to local model.",
                mcp_exc,
            )
            response = await resilient_ainvoke(
                self.model,
                [
                    SystemMessage(content="You are a senior frontend engineer. Return only valid, complete TSX source code."),
                    HumanMessage(content=prompt),
                ],
                "generate_single_page_code",
            )
            code = self._extract_tsx(response)
            logger.info("Generated page source directly: %s", page_path)

        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        with open(page_path, "w", encoding="utf-8") as page_file:
            page_file.write(code + "\n")
        return f"Generated {page_path}."
