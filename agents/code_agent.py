from schema.code import CodeGenerationOutput,CodeGenerationInput

from agents.llm import qwen_llm

from mcp_tools.initialize_mcps import run_mcp_agent,create_mcp_client
from mcp_tools.code_gent.storage import CodeStorage

import os
import re
import json
from pathlib import Path


CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)



SYSTEM_PROMPT = """
You are an expert frontend engineer.

Your task is to generate a complete website using:

- React
- TypeScript
- TailwindCSS
- GSAP

Use:

- User Prompt
- Research Output
- Design Output
- Page Output
- Asset Output
- Generated Assets
- Frame Extraction Output
- Context7 MCP for current React, TypeScript, TailwindCSS, GSAP, and React Router usage when you need library guidance.
- Filesystem MCP for all project file writes.

Rules:

- Create reusable React components.
- Use TailwindCSS for styling.
- Use GSAP for animations.
- Use generated assets. Every asset with status "success" in Generated Assets must be used in the relevant page or component unless it is technically impossible.
- Use extracted frames to understand motion and visual transitions.
- Generate production-ready code.
- Do not create demo, placeholder, sample, mock, under-construction, or "Content goes here" UI.
- Do not create generic filler pages. Every routed page must implement the sections, components, interactions, and content priorities from PAGE OUTPUT.
- Do not create duplicate page modules for the same page using different names.
- Implement the visual quality described in Design Output. Do NOT fall back to basic Tailwind styles (like plain blue buttons or flat white backgrounds).
- Use ultra-premium UI composition: Apple/Vercel/Linear style aesthetics. Use glassmorphism (`backdrop-blur-xl bg-white/5 border border-white/10`), subtle glowing radial gradients behind sections, tight typography leading, and high-contrast text.
- Use modern accent treatments like gradient text (`bg-clip-text text-transparent bg-gradient-to-r...`) for hero headlines and active states.
- Implement advanced motion from Design Output and Page Output. Use GSAP for page-load sequences, staggered card reveals, hover/lift states, CTA feedback, and scroll-triggered motion.
- CRITICAL: You MUST include parallax scrolling effects using GSAP ScrollTrigger for background images, floating elements, or hero sections. Make it feel alive.
- Register GSAP ScrollTrigger when using scroll-triggered animations.
- Use generated video or lottie assets when available for hero, background, product demo, or motion sections.
- If a generated video asset is available, render it with a muted autoplay loop video element in the relevant section.
- If a generated image asset is available, render it with an img, picture, CSS background, or component prop in the relevant section.
- Put static files that must be loaded by the browser under public/assets.
- Reference public assets in JSX with import.meta.env.BASE_URL, for example `${import.meta.env.BASE_URL}assets/images/example.png`.
- Do not use root-absolute asset URLs like /assets/images/example.png in JSX because the preview is served under /generated-preview/.
- CSS url(...) references should also be preview-safe and should not assume the app is hosted at domain root.
- React Router Rule: In `src/main.tsx`, just use `<BrowserRouter>`. No basename is required.
- Page Import Rule: In `src/main.tsx`, all page modules imported from `./pages/` MUST be imported as **default imports** (e.g., `import Homepage from './pages/Homepage'`), never as named imports (e.g., `import { Homepage }`), since they are default-exported.
- JSX Attribute Rule: Never write Javascript expressions, string concatenations, or variables directly inside a double-quoted JSX attribute (e.g., `className="bg-[url('" + BG_IMG + "')]"` is invalid). Any expression or concatenation in a JSX attribute MUST be enclosed in curly braces `{}` and preferably use template literals, for example: `className={`bg-[url('${BG_IMG}')]`}`.
- Heroicons Rule: If using `@heroicons/react` (v2), make sure to use correct v2 names. For example, use `BoltIcon` (not `LightningBoltIcon`), `LinkIcon` or `CommandLineIcon` (not `PlugIcon`), `GlobeAltIcon` (not `GlobeIcon`), etc. Avoid hallucinated icon names.

Filesystem rules:

- Write files only inside the output directory provided in the user prompt.
- Do not create or write to /app, D:\\app, or any path outside the output directory.
- Do not invent a different project root.
- The output directory and common subdirectories already exist.
- Write source files under src.
- Write static public files under public.
- If a write fails because a directory is missing, create the missing parent directory first, then retry once.

Return a concise summary of the files written.

After writing all required files, do not inspect or modify further.
Return final answer immediately with a concise list of files written.
Do not call directory_tree after final writes.

You must write a complete project before finishing:

- package.json
- index.html
- src/main.tsx
- src/index.css
- one page module under src/pages for every page in PAGE OUTPUT
- reusable component modules under src/components for the sections/components needed by those pages

Page and component filenames must match the generated PAGE OUTPUT.
Do not hardcode page names that are not present in PAGE OUTPUT.
If PAGE OUTPUT contains one page, create one page module for that page.
If PAGE OUTPUT contains multiple pages, create one module per page.
Use one naming convention only: PascalCase from page_name, for example "Blog" becomes Blog.tsx and "Pricing Page" becomes PricingPage.tsx.
src/main.tsx or src/App.tsx must import those exact page modules, not alternate duplicate files.

Invalid output examples:
- Pages containing only "Content goes here"
- Pages containing "under construction"
- Pages containing "placeholder", "demo", or "sample" instead of real sections
- Pages that do not use successful generated asset files
- Apps that route to Page.tsx while richer content exists in a different duplicate file

Do not return until all files are written.
Do not only describe the files.
Use the filesystem tool to create each file.
The exact tool name for writing files is write_file.
Never call write_file<|channel|>json or write_file<|channel|>commentary.

The output directories already exist.
Do not call create_directory.
Do not call directory_tree.
Use the filesystem write tool to write every required file.
"""



class CodeAgent:
  
    def __init__(self):
        self.model = qwen_llm()

    PLACEHOLDER_PATTERNS = [
        "content goes here",
        "under construction",
        "placeholder page",
        "placeholder content",
        "placeholder section",
        "dummy content",
        "mock content",
        "sample content",
        "replace with",
        "replace this",
        "coming soon",
        "demo content",
        "lorem ipsum",
        "todo",
    ]


    def _has_tsx_files(
        self,
        directory: str
    ) -> bool:

        return os.path.exists(directory) and any(
            file.endswith(".tsx")
            for file in os.listdir(directory)
        )


    def _module_name(
        self,
        name: str
    ) -> str:

        words = re.findall(
            r"[A-Za-z0-9]+",
            name
        )

        if not words:
            return "Page"

        return "".join(
            word[:1].upper() + word[1:]
            for word in words
        )


    def _expected_page_paths(
        self,
        code_input: CodeGenerationInput
    ) -> list[str]:

        return [
            os.path.join(
                OUTPUT_DIR,
                "src",
                "pages",
                f"{self._module_name(page.page_name)}.tsx"
            )
            for page in code_input.page_output.pages
        ]


    def _source_files(
        self
    ) -> list[Path]:

        src_dir = Path(OUTPUT_DIR) / "src"

        if not src_dir.exists():
            return []

        return [
            path
            for path in src_dir.rglob("*")
            if path.suffix in {".tsx", ".ts", ".css"}
        ]


    def _read_source_text(
        self
    ) -> str:

        chunks: list[str] = []

        for path in self._source_files():
            try:
                chunks.append(
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )
            except OSError:
                continue

        return "\n".join(chunks)


    def _placeholder_violations(
        self
    ) -> list[str]:

        violations: list[str] = []

        for path in self._source_files():
            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            except OSError:
                continue

            lowered = text.lower()

            for pattern in self.PLACEHOLDER_PATTERNS:
                if pattern in lowered:
                    violations.append(
                        f"{path}: contains '{pattern}'"
                    )
                    break

        return violations


    def _successful_asset_filenames(
        self,
        code_input: CodeGenerationInput
    ) -> list[str]:

        filenames: list[str] = []

        for asset in code_input.generated_asset_output.assets:
            if getattr(asset.status, "value", asset.status) != "success":
                continue

            if not asset.file_path:
                continue

            filename = os.path.basename(
                asset.file_path.replace("\\", "/")
            )

            if filename and filename not in filenames:
                filenames.append(filename)

        return filenames


    def _unused_successful_assets(
        self,
        code_input: CodeGenerationInput
    ) -> list[str]:

        source_text = self._read_source_text()

        if not source_text:
            return self._successful_asset_filenames(
                code_input
            )

        return [
            filename
            for filename in self._successful_asset_filenames(code_input)
            if filename not in source_text
        ]


    def _page_path(
        self,
        page_name: str
    ) -> str:

        return os.path.join(
            OUTPUT_DIR,
            "src",
            "pages",
            f"{self._module_name(page_name)}.tsx"
        )


    def _route_path(
        self,
        page_name: str,
        index: int
    ) -> str:

        if index == 0:
            return "/"

        words = re.findall(
            r"[A-Za-z0-9]+",
            page_name.lower()
        )

        return "/" + "-".join(words)


    def _page_asset_payload(
        self,
        code_input: CodeGenerationInput,
        page_name: str
    ) -> dict:

        page_key = page_name.lower()
        planned_assets = [
            asset
            for asset in code_input.asset_output.assets
            if asset.page_name.lower() == page_key
        ]
        planned_ids = {
            asset.asset_id
            for asset in planned_assets
        }
        generated_assets = [
            asset
            for asset in code_input.generated_asset_output.assets
            if (
                asset.source_asset_id in planned_ids
                or asset.asset_id in planned_ids
            )
        ]

        return {
            "planned_assets": [
                asset.model_dump(mode="json")
                for asset in planned_assets
            ],
            "generated_assets": [
                asset.model_dump(mode="json")
                for asset in generated_assets
            ],
        }


    def _page_successful_asset_filenames(
        self,
        code_input: CodeGenerationInput,
        page_name: str
    ) -> list[str]:

        payload = self._page_asset_payload(
            code_input,
            page_name
        )
        filenames: list[str] = []

        for asset in payload["generated_assets"]:
            if asset.get("status") != "success":
                continue

            file_path = asset.get("file_path")
            if not file_path:
                continue

            filename = os.path.basename(
                file_path.replace("\\", "/")
            )

            if filename:
                filenames.append(
                    filename
                )

        return filenames


    def _file_placeholder_violations(
        self,
        path: str
    ) -> list[str]:

        if not os.path.isfile(path):
            return [
                f"{path}: missing"
            ]

        text = Path(path).read_text(
            encoding="utf-8",
            errors="ignore"
        )
        lowered = text.lower()

        return [
            f"{path}: contains '{pattern}'"
            for pattern in self.PLACEHOLDER_PATTERNS
            if pattern in lowered
        ]


    def _page_unused_assets(
        self,
        code_input: CodeGenerationInput,
        page_name: str
    ) -> list[str]:

        page_path = self._page_path(
            page_name
        )

        if not os.path.isfile(page_path):
            return self._page_successful_asset_filenames(
                code_input,
                page_name
            )

        source_text = Path(page_path).read_text(
            encoding="utf-8",
            errors="ignore"
        )

        return [
            filename
            for filename in self._page_successful_asset_filenames(
                code_input,
                page_name
            )
            if filename not in source_text
        ]


    def _page_validation_errors(
        self,
        code_input: CodeGenerationInput,
        page_name: str
    ) -> list[str]:

        page_path = self._page_path(
            page_name
        )
        errors = self._file_placeholder_violations(
            page_path
        )
        errors.extend(
            f"{page_path}: does not reference generated asset '{filename}'"
            for filename in self._page_unused_assets(
                code_input,
                page_name
            )
        )

        return errors


    async def _run_project_shell_generation(
        self,
        code_input: CodeGenerationInput
    ) -> str:

        pages_summary = [
            {
                "page_name": page.page_name,
                "module": self._module_name(page.page_name),
                "route": self._route_path(index=index, page_name=page.page_name),
                "goal": page.page_goal,
            }
            for index, page in enumerate(code_input.page_output.pages)
        ]

        prompt = f"""
            OUTPUT DIRECTORY:
            {OUTPUT_DIR}

            Generate only the project shell and shared infrastructure.
            Do not generate page implementation files in this step.

            USER PROMPT:
            {code_input.user_prompt}

            PAGE ROUTES:
            {json.dumps(pages_summary, indent=2)}

            DESIGN OUTPUT:
            {code_input.design_output.model_dump_json(indent=2)}

            Requirements:
            - Use Context7 only if you need current library syntax.
            - Use Filesystem MCP write_file for file writes.
            - Write package.json, index.html, src/main.tsx, src/index.css, and reusable shared components under src/components.
            - src/main.tsx must import every page module listed in PAGE ROUTES using **default imports** (e.g., `import Homepage from './pages/Homepage'`), never named imports.
            - Page files may not exist yet. Still wire routes/imports to the exact future files.
            - Do not write any src/pages/*.tsx files in this step.
            - Implement shared layout, navigation, footer, animation helpers, asset helper, and GSAP setup.
            - Include React Router routes for every page, and configure the `BrowserRouter` with `basename={{import.meta.env.BASE_URL}}`.
            - Navigation must link to every page.
            - Use premium responsive visual foundations from DESIGN OUTPUT.
            - Include GSAP ScrollTrigger setup/helper patterns that pages can use.
            - Do not write placeholder, demo, sample, TODO, under construction, or Content goes here text.
            - Do not call create_directory or directory_tree.
            - Return concise summary after writing files.
            """

        return await run_mcp_agent(
            llm=self.model,
            prompt=prompt,
            allowed_servers=[
                "context7",
                "filesystem"
            ],
            system_prompt=SYSTEM_PROMPT,
            disallowed_tools=[
                "create_directory",
                "directory_tree"
            ],
            max_steps=45
        )


    async def _run_single_page_generation(
        self,
        code_input: CodeGenerationInput,
        *,
        page_index: int,
        repair_errors: list[str] | None = None
    ) -> str:

        page = code_input.page_output.pages[page_index]
        module_name = self._module_name(
            page.page_name
        )
        page_path = self._page_path(
            page.page_name
        )
        route_path = self._route_path(
            page.page_name,
            page_index
        )
        page_assets = self._page_asset_payload(
            code_input,
            page.page_name
        )

        prompt = f"""
            OUTPUT DIRECTORY:
            {OUTPUT_DIR}

            Generate exactly one page file:
            {page_path}

            Page module name:
            {module_name}

            Route:
            {route_path}

            This is page {page_index + 1} of {len(code_input.page_output.pages)}.
            Do not rewrite package.json, index.html, src/main.tsx, or unrelated pages.
            You may write focused reusable components only if this page needs them.

            USER PROMPT:
            {code_input.user_prompt}

            PAGE BLUEPRINT:
            {page.model_dump_json(indent=2)}

            GLOBAL PAGE RULES:
            {code_input.page_output.global_rules.model_dump_json(indent=2)}

            DESIGN OUTPUT:
            {code_input.design_output.model_dump_json(indent=2)}

            PAGE ASSETS:
            {json.dumps(page_assets, indent=2)}

            FRAME EXTRACTION OUTPUT:
            {code_input.frame_extraction_output.model_dump_json(indent=2)}

            PREVIOUS VALIDATION ERRORS TO FIX:
            {json.dumps(repair_errors or [], indent=2)}

            Requirements:
            - Use Filesystem MCP write_file to write {page_path}.
            - Use Context7 only if you need current syntax for React, GSAP, ScrollTrigger, Tailwind, or React Router.
            - The page must be complete, premium, responsive, and production-like.
            - Implement every section from PAGE BLUEPRINT in order.
            - Use section goals, layout strategies, component placements, interactions, animations, and content priorities from PAGE BLUEPRINT.
            - Use all PAGE ASSETS whose generated status is success. Reference public assets with import.meta.env.BASE_URL.
            - If PAGE ASSETS includes successful image/background assets, they must be visibly rendered in this page.
            - Implement ultra-premium UI aesthetics (Apple/Linear style). DO NOT use basic flat Tailwind classes. Use glassmorphism (`backdrop-blur-xl bg-white/5 border border-white/10`), sophisticated gradients, tight typography, glowing accents, and premium spacing.
            - Implement rich animations with GSAP: hero entrance, staggered card reveals, scroll-triggered section reveals, CTA hover/lift, and polished page transitions where suitable.
            - CRITICAL: You MUST implement parallax scrolling effects using GSAP ScrollTrigger on background images, decorative elements, or hero sections to create a sense of depth and premium feel.
            - Register ScrollTrigger if using scroll-based animation.
            - Animations must not depend on generated video assets.
            - Do not write placeholder, demo, mock, sample, TODO, under construction, Content goes here, Lorem Ipsum, coming soon, or dummy copy.
            - Do not use text saying assets should be replaced later.
            - Export default {module_name}.
            - Keep imports valid relative to generated_site/src.
            - Do not call create_directory or directory_tree.
            - Return concise summary after writing this page.
            """

        return await run_mcp_agent(
            llm=self.model,
            prompt=prompt,
            allowed_servers=[
                "context7",
                "filesystem"
            ],
            system_prompt=SYSTEM_PROMPT,
            disallowed_tools=[
                "create_directory",
                "directory_tree"
            ],
            max_steps=45
        )


    def _has_expected_page_files(
        self,
        code_input: CodeGenerationInput
    ) -> bool:

        expected_paths = self._expected_page_paths(
            code_input
        )

        return bool(expected_paths) and all(
            os.path.isfile(path)
            for path in expected_paths
        )


    async def _repair_missing_dynamic_files(
        self,
        code_input: CodeGenerationInput,
        *,
        pages_missing: bool,
        components_missing: bool,
        placeholder_violations: list[str] | None = None,
        unused_assets: list[str] | None = None
    ) -> None:

        placeholder_violations = placeholder_violations or []
        unused_assets = unused_assets or []

        if (
            not pages_missing
            and not components_missing
            and not placeholder_violations
            and not unused_assets
        ):
            return

        repair_prompt = f"""
            OUTPUT DIRECTORY:
            {OUTPUT_DIR}

            The previous code generation pass is invalid.
            Fix the generated React project directly in OUTPUT DIRECTORY.

            Do not call create_directory.
            Do not call directory_tree.
            Use only the exact write tool name: write_file.
            Never use tool names with channel suffixes like write_file<|channel|>json.

            Validation failures:
            - src/pages/*.tsx missing: {pages_missing}
            - src/components/*.tsx missing: {components_missing}
            - placeholder/demo violations:
              {chr(10).join(placeholder_violations) if placeholder_violations else "none"}
            - successful generated assets not referenced in source:
              {", ".join(unused_assets) if unused_assets else "none"}
            - exact page modules expected:
              {", ".join(self._expected_page_paths(code_input))}

            You must remove all placeholder/demo output.
            Do not write "Content goes here", "under construction", "placeholder", "demo", "sample", "TODO", or Lorem Ipsum anywhere.
            Do not create minimal pages just to satisfy file existence.
            Do not create duplicate page modules for the same route.

            Routing rules:
            - src/main.tsx or src/App.tsx must route to the exact PascalCase page modules from PAGE OUTPUT.
            - If PAGE OUTPUT has Blog, route to src/pages/Blog.tsx, not BlogPage.tsx.
            - If PAGE OUTPUT has "Pricing Page", route to src/pages/PricingPage.tsx.

            PAGE OUTPUT:
            {code_input.page_output.model_dump_json(indent=2)}

            DESIGN OUTPUT:
            {code_input.design_output.model_dump_json(indent=2)}

            GENERATED ASSETS:
            {code_input.generated_asset_output.model_dump_json(indent=2)}

            FRAME EXTRACTION OUTPUT:
            {code_input.frame_extraction_output.model_dump_json(indent=2)}

            Required:
            - Write or rewrite one complete page module under src/pages for each page in PAGE OUTPUT.
            - Page module filenames must be PascalCase from page_name, for example "Pricing Page" becomes src/pages/PricingPage.tsx.
            - Write reusable component modules under src/components.
            - Export default React components from page modules.
            - Import and reuse existing components where appropriate.
            - Keep imports valid relative to generated_site/src.
            - Preserve premium design quality and implement animations from PAGE OUTPUT.
            - Use every successful generated asset filename listed above in a relevant page or component.
            - Reference public assets with import.meta.env.BASE_URL.
            - Use GSAP motion for hero, cards, section reveals, and CTAs.
            - Return a concise summary only after writing the corrected files.
            """

        await run_mcp_agent(
            llm=self.model,
            prompt=repair_prompt,
            allowed_servers=[
                "context7",
                "filesystem"
            ],
            system_prompt=SYSTEM_PROMPT,
            disallowed_tools=[
                "create_directory",
                "directory_tree"
            ],
            max_steps=80
        )
        
    

    async def generate(
        self,
        code_input: CodeGenerationInput
    ) -> CodeGenerationOutput:

        for directory in [
            OUTPUT_DIR,
            os.path.join(OUTPUT_DIR, "src"),
            os.path.join(OUTPUT_DIR, "src", "components"),
            os.path.join(OUTPUT_DIR, "src", "pages"),
            os.path.join(OUTPUT_DIR, "src", "hooks"),
            os.path.join(OUTPUT_DIR, "src", "lib"),
            os.path.join(OUTPUT_DIR, "src", "assets"),
            os.path.join(OUTPUT_DIR, "public"),
            os.path.join(OUTPUT_DIR, "assets"),
            os.path.join(OUTPUT_DIR, "assets", "images"),
        ]:
            os.makedirs(
                directory,
                exist_ok=True
            )
        
        summaries: list[str] = []

        summaries.append(
            await self._run_project_shell_generation(
                code_input
            )
        )

        for page_index, page in enumerate(code_input.page_output.pages):
            print(
                f"Code page started: {page.page_name}"
            )

            page_errors: list[str] = []
            max_page_attempts = int(
                os.getenv(
                    "CODE_PAGE_GENERATION_ATTEMPTS",
                    "4"
                )
            )

            for attempt in range(1, max_page_attempts + 1):
                summaries.append(
                    await self._run_single_page_generation(
                        code_input,
                        page_index=page_index,
                        repair_errors=page_errors if attempt > 1 else None
                    )
                )

                page_errors = self._page_validation_errors(
                    code_input,
                    page.page_name
                )

                if not page_errors:
                    break

                print(
                    f"Code page repair needed: {page.page_name} "
                    f"attempt {attempt}/{max_page_attempts}"
                )

            if page_errors:
                raise RuntimeError(
                    f"Code agent failed validation for page "
                    f"{page.page_name}: "
                    + "; ".join(page_errors[:10])
                )

            print(
                f"Code page finished: {page.page_name}"
            )

        result = "\n".join(
            str(summary)
            for summary in summaries
        )

        pages_dir = os.path.join(
            OUTPUT_DIR,
            "src",
            "pages"
        )
        components_dir = os.path.join(
            OUTPUT_DIR,
            "src",
            "components"
        )

        has_pages = self._has_expected_page_files(
            code_input
        )
        has_components = self._has_tsx_files(
            components_dir
        )
        placeholder_violations = self._placeholder_violations()
        unused_assets = self._unused_successful_assets(
            code_input
        )

        if (
            not has_pages
            or not has_components
            or placeholder_violations
            or unused_assets
        ):
            await self._repair_missing_dynamic_files(
                code_input,
                pages_missing=not has_pages,
                components_missing=not has_components,
                placeholder_violations=placeholder_violations,
                unused_assets=unused_assets
            )

            has_pages = self._has_expected_page_files(
                code_input
            )
            has_components = self._has_tsx_files(
                components_dir
            )
            placeholder_violations = self._placeholder_violations()
            unused_assets = self._unused_successful_assets(
                code_input
            )

        if not has_pages or not has_components:
            raise RuntimeError(
                "Code agent finished but did not generate every dynamic src/pages file and src/components files from PAGE OUTPUT"
            )

        if placeholder_violations:
            raise RuntimeError(
                "Code agent finished with placeholder/demo content: "
                + "; ".join(placeholder_violations[:10])
            )

        if unused_assets:
            logger.warning(
                "Code agent finished without using every successful generated asset: "
                + ", ".join(unused_assets[:20])
            )

        return result
    
