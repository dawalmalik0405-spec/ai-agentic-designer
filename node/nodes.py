from schema.state import WebsiteBuilderState

from agents.architect_agent import ArchitectAgent
from agents.research_agent import ResearchAgent
from agents.designing_agent import DesigningAgent
from agents.page_agent import PageAgent
from agents.asset_agent import AssetAgent
from agents.gen_agent import GenerationAgent
from agents.frame_extraction_agent import FrameExtractionAgent

from mcp_tools.frame_extraction.extractor import ( FrameExtractor )

from schema.code import CodeGenerationInput




async def architect_node(
    state: WebsiteBuilderState
):
    print("arch agent started")
    agent = ArchitectAgent()

    result = await agent.build_architecture(
        state["user_prompt"],
        selected_style=state["selected_style"]
    )

    print("arch agent finished")

    return {
        "architect_output": result
    }




async def research_node(
        state:WebsiteBuilderState
):
    
    print("rese agent started")
    agent  =  ResearchAgent()

    result = await agent.research(
        state["architect_output"]
    )
    print("reserr agent finished")

    return{
        "research_output":result
    }


async def design_node(
    state: WebsiteBuilderState
):
    print("desighn agent started")

    agent = DesigningAgent()

    result = await agent.design_system(
        architect_output=state["architect_output"],
        research_output=state["research_output"]
    )

    print("dessign agent finished")

    return {
        "design_system_output": result
    }



async def page_node(
    state: WebsiteBuilderState
):

    print("page started")
    agent = PageAgent()

    result = await agent.design_single_page(
        architect_output=state["architect_output"],
        design_output=state["design_system_output"]
    )

    print("page finished")
    return {
        "page_design_output": result
    }



async def asset_node(
    state: WebsiteBuilderState
):

    print("asset started ")
    agent = AssetAgent()

    result = await agent.plan_assets(
        state["page_design_output"]
    )

    print("asset finished ")

    return {
        "asset_output": result
    }



async def generation_node(
    state: WebsiteBuilderState
):
    
    print("gen started")

    agent = GenerationAgent()

    result = await agent.generate(
        state["asset_output"]
    )
    print("gen finished ")

    return {
        "generated_asset_output": result
    }




async def frame_extraction_node(
    state: WebsiteBuilderState
):
    print("frame started")

    agent = FrameExtractionAgent()

    result = await agent.extract(
        state["generated_asset_output"]
    )

    print("frame finished")
    return {
        "frame_extraction_output": result
    }





async def assembly_node(
    state: WebsiteBuilderState
):
    print("assembly started ")
    from agents.asset_injection_agent import AssetInjectionAgent
    import os
    
    injector = AssetInjectionAgent()
    
    assets_mapping = {}
    if state.get("generated_asset_output"):
        for asset in state["generated_asset_output"].assets:
            if asset.status.value == "success" and asset.file_path:
                filename = os.path.basename(asset.file_path)
                assets_mapping[asset.asset_id] = f"/assets/{filename}"
                
    # Inject into each page
    if state.get("page_design_output"):
        for page in state["page_design_output"].pages:
            try:
                await injector.inject_assets_to_page(state, page.page_name, assets_mapping)
            except Exception as e:
                print(f"Failed to inject assets into page {page.page_name}: {e}")
                
    print("assembly finished ")
    return {
        "generated_code": "Assets successfully injected into pages."
    }
