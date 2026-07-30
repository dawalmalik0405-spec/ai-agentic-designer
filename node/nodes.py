from schema.state import WebsiteBuilderState

from agents.architect_agent import ArchitectAgent
from agents.research_agent import ResearchAgent
from agents.designing_agent import DesigningAgent
from agents.page_agent import PageAgent
from agents.asset_agent import AssetAgent
from agents.gen_agent import GenerationAgent

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










async def assembly_node(
    state: WebsiteBuilderState
):
    return {
        "generated_code": "Asset injection has been removed from the pipeline."
    }
