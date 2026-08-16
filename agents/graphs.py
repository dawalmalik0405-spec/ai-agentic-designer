from langgraph.graph import (
    StateGraph,
    START,
    END
)

from schema.state import WebsiteBuilderState, AssetGenerationState, MotionGenerationState, AssetInjectionState, AddPageState


from node.nodes import (
    architect_node,
    research_node,
    design_node,
    page_node,
    page_code_node,
    asset_node,
    generation_node,
    asset_injection_node,
    asset_injection_dev_server_node,
    add_page_architect_node,
    add_page_research_node,
    add_page_design_node,
    add_page_page_node,
    add_page_code_node,
    add_page_route_node,
    add_page_dev_server_node,
    motion_node,
    motion_inject_node
)


import asyncio
import os


CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
GENERATED_SITE_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)




#---------page------------


builder = StateGraph(
    WebsiteBuilderState
)

builder.add_node(
    "architect",
    architect_node
)

builder.add_node(
    "research",
    research_node
)

builder.add_node(
    "design",
    design_node
)

builder.add_node(
    "page",
    page_node
)

builder.add_node(
    "page_code",
    page_code_node
)


builder.add_edge(
    START,
    "architect"
)

builder.add_edge(
    "architect",
    "research"
)

builder.add_edge(
    "research",
    "design"
)

builder.add_edge(
    "design",
    "page"
)

builder.add_edge(
    "page",
    "page_code"
)

builder.add_edge(
    "page_code",
    END
)




graph = builder.compile()


#------graph2--------------


asset =  StateGraph(
    AssetGenerationState
)

asset.add_node(
    "asset_plan",
    asset_node
)

asset.add_node(
    "asset_gen",
    generation_node
)


asset.add_edge(
    START,
    "asset_plan"
)

asset.add_edge(
    "asset_plan",
    "asset_gen"
)

asset.add_edge(
    "asset_gen",
    END
)


asset_graph = asset.compile()

#--------------------------------------

def _asset_initial_state(
    page_design_output,
    design_system_output,
    page_code_output,
) -> AssetGenerationState:

    return {
        "page_design_output": page_design_output,
        "design_system_output": design_system_output,
        "page_code_output": page_code_output,

        "asset_output": None,
        "generated_asset_output": None,
    }


async def run_asset_graph_async(
    page_design_output,
    design_system_output,
    page_code_output,
):

    state = _asset_initial_state(
        page_design_output,
        design_system_output,
        page_code_output,
    )

    result = await asset_graph.ainvoke(state)

    return result



#------ motion --------------------------------------------
motion = StateGraph(MotionGenerationState)

motion.add_node(
    "motion_plan",
    motion_node
)

motion.add_node(
    "motion_inject",
    motion_inject_node
)

motion.add_edge(
    START,
    "motion_plan"
)

motion.add_edge(
    "motion_plan",
    "motion_inject"
)

motion.add_edge(
    "motion_inject",
    END
)

motion_graph = motion.compile()



def _motion_initial_state(
    design_system_output,
    page_design_output,
    page_code_output,
    generated_asset_output,
) -> MotionGenerationState:

    return {

        "design_system_output": design_system_output,

        "page_design_output": page_design_output,

        "page_code_output": page_code_output,

        "generated_asset_output": generated_asset_output,

        "motion_output": None,

        "final_page_code_output": None,
    }




async def run_motion_graph_async(
    page_design_output,
    design_system_output,
    page_code_output,
    generated_asset_output,
):

    state = _motion_initial_state(
        page_design_output,
        design_system_output,
        page_code_output,
        generated_asset_output,
    )

    result = await motion_graph.ainvoke(state)

    return result


#------ asset injection --------------------------------------------
asset_injection = StateGraph(AssetInjectionState)

asset_injection.add_node(
    "asset_injection",
    asset_injection_node
)

asset_injection.add_node(
    "dev_server",
    asset_injection_dev_server_node
)

asset_injection.add_edge(
    START,
    "asset_injection"
)

asset_injection.add_edge(
    "asset_injection",
    "dev_server"
)

asset_injection.add_edge(
    "dev_server",
    END
)

asset_injection_graph = asset_injection.compile()


def _asset_injection_initial_state(
    project_id: str,
    approved_assets=None,
    generated_site_dir: str | None = None,
    target_page_name: str | None = None,
) -> AssetInjectionState:

    return {
        "project_id": project_id,
        "generated_site_dir": generated_site_dir,
        "target_page_name": target_page_name,
        "approved_assets": approved_assets,
        "injection_output": None,
        "dev_server_status": None,
        "preview_url": None,
        "log_tail": [],
    }


async def run_asset_injection_graph_async(
    project_id: str,
    approved_assets=None,
    generated_site_dir: str | None = None,
    target_page_name: str | None = None,
) -> AssetInjectionState:

    state = _asset_injection_initial_state(
        project_id=project_id,
        approved_assets=approved_assets,
        generated_site_dir=generated_site_dir,
        target_page_name=target_page_name,
    )

    result = await asset_injection_graph.ainvoke(state)

    return result


#------ add page --------------------------------------------
add_page = StateGraph(AddPageState)

add_page.add_node("architect", add_page_architect_node)
add_page.add_node("research", add_page_research_node)
add_page.add_node("design", add_page_design_node)
add_page.add_node("page", add_page_page_node)
add_page.add_node("page_code", add_page_code_node)
add_page.add_node("route_update", add_page_route_node)
add_page.add_node("dev_server", add_page_dev_server_node)

add_page.add_edge(START, "architect")
add_page.add_edge("architect", "research")
add_page.add_edge("research", "design")
add_page.add_edge("design", "page")
add_page.add_edge("page", "page_code")
add_page.add_edge("page_code", "route_update")
add_page.add_edge("route_update", "dev_server")
add_page.add_edge("dev_server", END)

add_page_graph = add_page.compile()


def _add_page_initial_state(
    project_id: str,
    page_name: str,
    prompt: str,
    selected_style: str,
    existing_architect_output,
    existing_research_output,
    existing_design_system_output,
    existing_page_design_output,
    generated_site_dir: str | None = None,
) -> AddPageState:

    return {
        "project_id": project_id,
        "page_name": page_name,
        "user_prompt": prompt,
        "selected_style": selected_style,
        "generated_site_dir": generated_site_dir,
        "existing_architect_output": existing_architect_output,
        "existing_research_output": existing_research_output,
        "existing_design_system_output": existing_design_system_output,
        "existing_page_design_output": existing_page_design_output,
        "architect_output": None,
        "research_output": None,
        "design_system_output": None,
        "page_design_output": None,
        "page_code_output": None,
        "add_page_output": None,
    }


async def run_add_page_graph_async(
    project_id: str,
    page_name: str,
    prompt: str,
    selected_style: str,
    existing_architect_output,
    existing_research_output,
    existing_design_system_output,
    existing_page_design_output,
    generated_site_dir: str | None = None,
) -> AddPageState:

    state = _add_page_initial_state(
        project_id=project_id,
        page_name=page_name,
        prompt=prompt,
        selected_style=selected_style,
        existing_architect_output=existing_architect_output,
        existing_research_output=existing_research_output,
        existing_design_system_output=existing_design_system_output,
        existing_page_design_output=existing_page_design_output,
        generated_site_dir=generated_site_dir,
    )

    result = await add_page_graph.ainvoke(state)

    return result






#-------------- Edit (NOT YET IMPLEMENTED - nodes/state pending) ---------------
# Uncomment and wire when edit nodes are ready:
#
# from schema.state import EditState
# from node.edit_nodes import (
#     intent_classifier_node, dependency_analyzer_node,
#     file_selector_node, targeted_edit_node, build_check_node
# )
#
# edit_builder = StateGraph(EditState)
# edit_builder.add_node("intent",       intent_classifier_node)
# edit_builder.add_node("dependency",   dependency_analyzer_node)
# edit_builder.add_node("file_selector",file_selector_node)
# edit_builder.add_node("edit",         targeted_edit_node)
# edit_builder.add_node("build_check",  build_check_node)
# edit_builder.add_edge(START,           "intent")
# edit_builder.add_edge("intent",        "dependency")
# edit_builder.add_edge("dependency",    "file_selector")
# edit_builder.add_edge("file_selector", "edit")
# edit_builder.add_edge("edit",          "build_check")
# edit_builder.add_edge("build_check",   END)
# edit_graph = edit_builder.compile()
#-------------------------------------------------------------------------------


# def _initial_state(






#---------------------------------------








def _initial_state(
    prompt: str,
    selected_style: str
) -> WebsiteBuilderState:
    return {
        "user_prompt": prompt,
        "selected_style": selected_style,
        "architect_output": None,
        "research_output": None,
        "design_system_output": None,
        "page_design_output": None,
        "page_code_output": None,
    }




async def run_graph_async(
    prompt: str,
    selected_style: str
) -> WebsiteBuilderState:

    state = _initial_state(
        prompt,
        selected_style
    )

    result = await graph.ainvoke(state)

    return result




#--------------------------------







async def run_graph_events(
    prompt: str,
    selected_style: str,
):
    state = _initial_state(prompt, selected_style)

    async for event in graph.astream(state):
        yield event


async def main():

    result = await run_graph_async(
        prompt="Create a futuristic AI startup website home page ",
        selected_style="skeumorphism"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
