from schema.code import CodeGenerationOutput,CodeGenerationInput

from agents.llm import qwen_llm

from mcp_tools.initialize_mcps import run_mcp_agent,create_mcp_client
from mcp_tools.code_gent.storage import CodeStorage



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

Return all files required for the project.
"""



class CodeAgent:
  
    
    model = qwen_llm()
        
    

    async def generate(
        self,
        code_input: CodeGenerationInput
    ) -> CodeGenerationOutput:
        
        prompt = f"""
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
    


