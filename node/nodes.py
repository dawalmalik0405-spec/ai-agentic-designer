from schema.state import WebsiteBuilderState, AssetGenerationState, AssetInjectionState, AddPageState

from agents.architect_agent import ArchitectAgent
from agents.research_agent import ResearchAgent
from agents.designing_agent import DesigningAgent
from agents.page_agent import PageAgent
from agents.page_code_agent import PageCodeAgent
from agents.asset_agent import AssetAgent
from agents.gen_agent import GenerationAgent
from agents.motion_agent import MotionAgent
from agents.asset_injection_agent import AssetInjectionAgent
from schema.add_page import AddPageOutput

import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Graph 1 – Website Builder Pipeline
# ─────────────────────────────────────────────

async def architect_node(state: WebsiteBuilderState):
    print("arch agent started")
    agent = ArchitectAgent()
    result = await agent.build_architecture(
        state["user_prompt"],
        selected_style=state["selected_style"]
    )
    print("arch agent finished")
    return {"architect_output": result}


async def research_node(state: WebsiteBuilderState):
    print("research agent started")
    agent = ResearchAgent()
    result = await agent.research(state["architect_output"])
    print("research agent finished")
    return {"research_output": result}


async def design_node(state: WebsiteBuilderState):
    print("design agent started")
    agent = DesigningAgent()
    result = await agent.design_system(
        architect_output=state["architect_output"],
        research_output=state["research_output"]
    )
    print("design agent finished")
    return {"design_system_output": result}


async def page_node(state: WebsiteBuilderState):
    print("page agent started")
    agent = PageAgent()
    result = await agent.design_single_page(
        architect_output=state["architect_output"],
        design_output=state["design_system_output"]
    )
    print("page agent finished")
    return {"page_design_output": result}


async def page_code_node(state: WebsiteBuilderState):
    """Generates the project shell + individual page code files."""
    print("page_code agent started")
    agent = PageCodeAgent()

    # Step 1: Write package.json, index.html, tsconfig, main.tsx, shared components
    await agent.generate_project_shell(state)

    # Step 2: Generate a TSX file for every page in the blueprint
    pages = state["page_design_output"].pages
    for page in pages:
        try:
            await agent.generate_single_page(state, page.page_name)
            print(f"  ✓ Generated page: {page.page_name}")
        except Exception as exc:
            logger.warning(f"Page code generation failed for '{page.page_name}': {exc}")

    # Step 3: Install dependencies and start the dev server
    print("Starting npm install and dev server...")
    build_result = await agent.install_and_start_dev_server()
    
    print("page_code agent finished")
    
    from schema.code import CodeGenerationOutput, GeneratedFile
    # Return the status in the CodeGenerationOutput schema
    output = CodeGenerationOutput(
        files=[], # Files were already written to disk
        build_status=build_result["build_status"],
        preview_url=build_result["preview_url"]
    )
    return {"page_code_output": output}


# ─────────────────────────────────────────────
# Graph 2 – Asset Generation Pipeline
# ─────────────────────────────────────────────

async def asset_node(state: AssetGenerationState):
    """Plans visual assets using full pipeline context."""
    print("asset agent started")
    agent = AssetAgent()
    result = await agent.plan_assets(
        page_design_output=state["page_design_output"],
        design_system_output=state.get("design_system_output"),
    )
    print("asset agent finished")
    return {"asset_output": result}


async def generation_node(state: AssetGenerationState):
    """Generates all planned assets via Pollinations / Unsplash."""
    print("generation agent started")
    agent = GenerationAgent()
    result = await agent.generate(state["asset_output"])
    print("generation agent finished")
    return {"generated_asset_output": result}


async def asset_injection_node(state: AssetInjectionState):
    """Injects approved assets into generated page TSX files."""
    print("asset injection agent started")
    agent = AssetInjectionAgent()
    result = await agent.inject(
        approved_assets=state.get("approved_assets"),
        generated_site_dir=state.get("generated_site_dir") or None,
        target_page_name=state.get("target_page_name"),
    )
    print("asset injection agent finished")
    return {"injection_output": result}


async def asset_injection_dev_server_node(state: AssetInjectionState):
    """Starts the generated-site dev server after asset injection."""
    print("asset injection dev server started")
    agent = AssetInjectionAgent()
    result = await agent.start_dev_server(
        generated_site_dir=state.get("generated_site_dir") or None,
    )

    injection_output = state.get("injection_output")
    if injection_output:
        injection_output.dev_server_status = result["dev_server_status"]
        injection_output.preview_url = result["preview_url"]
        injection_output.log_tail = result["log_tail"]

    print("asset injection dev server finished")
    return {
        "injection_output": injection_output,
        "dev_server_status": result["dev_server_status"],
        "preview_url": result["preview_url"],
        "log_tail": result["log_tail"],
    }


async def add_page_architect_node(state: AddPageState):
    print("add page architect agent started")
    agent = ArchitectAgent()
    prompt = f"""
Existing project architecture:
{state["existing_architect_output"].model_dump_json(indent=2)}

Add exactly one new page to this existing project.

New page name: {state["page_name"]}
New page request: {state["user_prompt"]}

Return architecture for this add-page task only.
Include exactly one page_blueprint for the new page.
Do not create a new website.
Do not include existing pages as page_blueprints.
"""
    result = await agent.build_architecture(
        prompt=prompt,
        selected_style=state["selected_style"],
    )
    if result.page_blueprints:
        result.page_blueprints = result.page_blueprints[:1]
        result.page_blueprints[0].name = state["page_name"]
    print("add page architect agent finished")
    return {"architect_output": result}


async def add_page_research_node(state: AddPageState):
    print("add page research agent started")
    agent = ResearchAgent()
    result = await agent.research(state["architect_output"])
    print("add page research agent finished")
    return {"research_output": result}


async def add_page_design_node(state: AddPageState):
    print("add page design agent started")
    agent = DesigningAgent()
    result = await agent.design_system(
        architect_output=state["architect_output"],
        research_output=state["research_output"],
    )
    print("add page design agent finished")
    return {"design_system_output": result}


async def add_page_page_node(state: AddPageState):
    print("add page page agent started")
    agent = PageAgent()
    result = await agent.design_single_page(
        architect_output=state["architect_output"],
        design_output=state["design_system_output"],
    )
    if result.pages:
        result.pages[0].page_name = state["page_name"]
    print("add page page agent finished")
    return {"page_design_output": result}


async def add_page_code_node(state: AddPageState):
    print("add page code agent started")
    agent = PageCodeAgent()
    result = await agent.generate_added_page(state)
    from schema.code import CodeGenerationOutput

    output = CodeGenerationOutput(files=[])
    add_page_output = AddPageOutput(
        page_name=state["page_name"],
        route=result["route"],
        file_path=result["file_path"],
    )
    print("add page code agent finished")
    return {
        "page_code_output": output,
        "add_page_output": add_page_output,
    }


async def add_page_route_node(state: AddPageState):
    print("add page route update started")
    agent = PageCodeAgent()
    result = agent.add_page_route(state["page_name"])
    add_page_output = state.get("add_page_output")
    if add_page_output:
        add_page_output.route = result["route"]
        add_page_output.file_path = result["file_path"]
    print("add page route update finished")
    return {"add_page_output": add_page_output}


async def add_page_dev_server_node(state: AddPageState):
    print("add page dev server started")
    agent = PageCodeAgent()
    result = await agent.install_and_start_dev_server()
    add_page_output = state.get("add_page_output")
    if add_page_output:
        add_page_output.preview_url = result.get("preview_url")
        add_page_output.dev_server_status = result.get("build_status")
        add_page_output.log_tail = result.get("log_tail", [])
    print("add page dev server finished")
    return {"add_page_output": add_page_output}


# ─────────────────────────────────────────────
# Motion Graph Nodes (Graph 3 – not yet tested)
# ─────────────────────────────────────────────

async def motion_node(state):
    print("motion agent started")
    agent = MotionAgent()
    result = await agent.generate_motion(
        architecture=state["architect_output"] if "architect_output" in state else None,
        design_system=state["design_system_output"],
        page_design=state["page_design_output"],
        asset_registry=state.get("asset_output"),
    )
    print("motion agent finished")
    return {"motion_output": result}


async def motion_inject_node(state):
    """Placeholder — motion injection into code not yet implemented."""
    print("motion_inject_node: not yet implemented, skipping.")
    return {"final_page_code_output": None}


# ─────────────────────────────────────────────
# Legacy / unused
# ─────────────────────────────────────────────

async def assembly_node(state):
    return {"generated_code": "Asset injection has been removed from the pipeline."}
