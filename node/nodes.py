from schema.state import WebsiteBuilderState

from agents.architect_agent import ArchitectAgent
from agents.research_agent import ResearchAgent
from agents.designing_agent import DesigningAgent
from agents.page_agent import PageAgent
from agents.asset_agent import AssetAgent
from agents.gen_agent import GenerationAgent
from agents.code_agent import CodeAgent
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

    result = await agent.design_pages(
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




async def code_node(
    state: WebsiteBuilderState
):
    
    print("code started ")

    agent = CodeAgent()

    code_input = CodeGenerationInput(
        user_prompt=state["user_prompt"],
        architect_output=state["architect_output"],
        research_output=state["research_output"],
        design_output=state["design_system_output"],
        page_output=state["page_design_output"],
        asset_output=state["asset_output"],
        generated_asset_output=state["generated_asset_output"],
        frame_extraction_output=state["frame_extraction_output"]
    )

    result = await agent.generate(
        code_input
    )

    print("code finished ")

    return {
        "generated_code": result
    }