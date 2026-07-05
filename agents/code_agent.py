from schema.code import CodeGenerationOutput,CodeGenerationInput

from agents.llm import qwen_llm

from mcp_tools.initialize_mcps import run_mcp_agent,create_mcp_client
from mcp_tools.code_gent.storage import CodeStorage

import os


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

Rules:

- Create reusable React components.
- Use TailwindCSS for styling.
- Use GSAP for animations.
- Use generated assets when available.
- Use extracted frames to understand motion and visual transitions.
- Generate production-ready code.

Filesystem rules:

- Write files only inside the output directory provided in the user prompt.
- Do not create or write to /app, D:\\app, or any path outside the output directory.
- Do not invent a different project root.
- The output directory and common subdirectories already exist.
- Write source files under src.
- Write static public files under public.
- If a write fails because a directory is missing, create the missing parent directory first, then retry once.

Return a concise summary of the files written.
"""



class CodeAgent:
  
    
    model = qwen_llm()
        
    

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
        ]:
            os.makedirs(
                directory,
                exist_ok=True
            )
        
        prompt = f"""
            OUTPUT DIRECTORY:
            {OUTPUT_DIR}

            Write the generated project directly into this exact directory.
            Do not create another top-level app folder.

            USER PROMPT:
            {code_input.user_prompt}

            DESIGN OUTPUT:
            {code_input.design_output.model_dump_json(indent=2)}

            PAGE OUTPUT:
            {code_input.page_output.model_dump_json(indent=2)}

            GENERATED ASSETS:
            {code_input.generated_asset_output.model_dump_json(indent=2)}

            FRAME EXTRACTION OUTPUT:
            {code_input.frame_extraction_output.model_dump_json(indent=2)}

            Generate a complete React + TypeScript + TailwindCSS + GSAP project.
            """

        return await run_mcp_agent(
           
            llm= self.model,
            prompt=prompt,
            allowed_servers=[
                "context7",
                "filesystem"
            ],
            system_prompt=SYSTEM_PROMPT,
            max_steps=20
        )
    

