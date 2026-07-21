from agents.llm import mcp_code_llm
from mcp_tools.initialize_mcps import run_mcp_agent
import os
import json
import logging

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)

SYSTEM_PROMPT = """
You are an expert frontend engineer.

Your task is to take a fully generated React codebase and inject the final generated visual assets into the pages and components.

You have access to:
- Filesystem MCP for reading and writing project files.

Rules:
- The website is already built using React, TypeScript, and TailwindCSS.
- Pages currently use `placehold.co` or other generic URLs for images and videos.
- You must find all components and pages in `src/pages` and `src/components` that need assets.
- Replace the placeholder URLs with the actual paths of the successfully generated assets.
- For images and videos, reference public assets using `import.meta.env.BASE_URL`, e.g., `${import.meta.env.BASE_URL}assets/images/example.png`.
- Do not make stylistic or structural changes to the code. Only replace asset URLs.
- After updating the files, return a concise summary of the files modified.
"""

class AssemblyAgent:
    def __init__(self):
        self.model = mcp_code_llm()

    async def assemble(self, state: dict) -> str:
        if not state.get("generated_asset_output"):
            return "No assets to assemble."

        successful_assets = [
            asset.model_dump(mode="json")
            for asset in state["generated_asset_output"].assets
            if asset.status.value == "success" and asset.file_path
        ]

        if not successful_assets:
            return "No successful assets to assemble."

        prompt = f"""
        OUTPUT DIRECTORY:
        {OUTPUT_DIR}

        GENERATED ASSETS:
        {json.dumps(successful_assets, indent=2)}

        Task:
        1. Examine the source code in {OUTPUT_DIR}/src/pages and {OUTPUT_DIR}/src/components.
        2. Identify where placeholders (like placehold.co) are used.
        3. Replace them with the actual paths of the generated assets provided above.
        4. Remember to use `${{import.meta.env.BASE_URL}}` for all asset paths (e.g. `${{import.meta.env.BASE_URL}}assets/images/hero.png`).
        """

        return await run_mcp_agent(
            llm=self.model,
            prompt=prompt,
            allowed_servers=["filesystem"],
            system_prompt=SYSTEM_PROMPT,
            disallowed_tools=["create_directory", "directory_tree"],
            max_steps=40
        )
