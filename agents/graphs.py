from langgraph.graph import (
    StateGraph,
    START,
    END
)

from schema.state import WebsiteBuilderState

from node.nodes import (
    architect_node,
    research_node,
    design_node,
    page_node,
    asset_node,
    generation_node,
    frame_extraction_node,
    assembly_node
)

import asyncio
import os


CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
GENERATED_SITE_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)

PIPELINE_NODES = [
    ("architect", "Planning website architecture", architect_node),
    ("research", "Researching references and patterns", research_node),
    ("design", "Creating design system", design_node),
    ("page", "Designing page blueprints", page_node),
    ("asset", "Planning visual assets", asset_node),
    ("generation", "Generating visual assets", generation_node),
    ("frame_extraction", "Extracting motion frames", frame_extraction_node),
    ("assembly", "Assembling final project", assembly_node),
]

# The draft stage deliberately stops before assets or code are produced.  It is
# used by the review UI so a user can approve the page structure first.
DESIGN_PIPELINE_NODES = PIPELINE_NODES[:4]
BUILD_PIPELINE_NODES = PIPELINE_NODES[5:]


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
    "asset",
    asset_node
)

builder.add_node(
    "generation",
    generation_node
)

builder.add_node(
    "frame_extraction",
    frame_extraction_node
)

builder.add_node(
    "assembly",
    assembly_node
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
    "asset"
)

builder.add_edge(
    "asset",
    "generation"
)

builder.add_edge(
    "generation",
    "frame_extraction"
)

builder.add_edge(
    "frame_extraction",
    "assembly"
)

builder.add_edge(
    "assembly",
    END
)



graph = builder.compile()


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
        "asset_output": None,
        "generated_asset_output": None,
        "frame_extraction_output": None,
        "generated_code": None,
    }


def _generated_code_files() -> list[str]:
    if not os.path.isdir(GENERATED_SITE_DIR):
        return []

    allowed_extensions = {
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".css",
        ".html",
        ".json",
        ".config.js",
        ".config.ts",
    }
    ignored_dirs = {
        "node_modules",
        "dist",
        ".vite",
    }
    files: list[str] = []

    for root, dirs, names in os.walk(GENERATED_SITE_DIR):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in ignored_dirs
        ]

        for name in names:
            full_path = os.path.join(root, name)
            relative_path = os.path.relpath(
                full_path,
                GENERATED_SITE_DIR
            ).replace(os.sep, "/")

            if (
                any(name.endswith(extension) for extension in allowed_extensions)
                or relative_path in {"package.json", "vite.config.ts", "tailwind.config.js"}
            ):
                files.append(relative_path)

    return sorted(files)


async def run_graph_async(
    prompt: str,
    selected_style: str
) -> WebsiteBuilderState:
    state = _initial_state(
        prompt,
        selected_style
    )

    for _, _, node in PIPELINE_NODES:
        update = await node(state)
        state.update(update)

    return state


async def run_design_preview_async(
    prompt: str,
    selected_style: str
) -> WebsiteBuilderState:
    state = _initial_state(prompt, selected_style)

    for _, _, node in DESIGN_PIPELINE_NODES:
        update = await node(state)
        state.update(update)

    return state


async def plan_assets_async(
    state: WebsiteBuilderState
) -> WebsiteBuilderState:
    update = await asset_node(state)
    state.update(update)
    return state


async def run_approved_build_async(
    state: WebsiteBuilderState
) -> WebsiteBuilderState:
    if state.get("asset_output") is None:
        raise ValueError("Assets must be selected before code generation.")

    build_nodes = BUILD_PIPELINE_NODES
    if state.get("generated_asset_output") is not None:
        build_nodes = [
            item for item in BUILD_PIPELINE_NODES
            if item[0] != "generation"
        ]

    for _, _, node in build_nodes:
        update = await node(state)
        state.update(update)

    return state


def run_graph(
    prompt: str,
    selected_style: str
) -> WebsiteBuilderState:
    return asyncio.run(
        run_graph_async(
            prompt,
            selected_style
        )
    )


async def run_graph_events(
    prompt: str,
    selected_style: str
):
    state = _initial_state(
        prompt,
        selected_style
    )
    seen_files: set[str] = set()

    for name, label, node in PIPELINE_NODES:
        yield {
            "type": "step",
            "step": name,
            "label": label,
            "status": "started",
        }

        update = await node(state)

        if name == "assembly":
            for file_path in _generated_code_files():
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)
                yield {
                    "type": "file",
                    "path": file_path,
                    "status": "written",
                }

        state.update(update)

        yield {
            "type": "step",
            "step": name,
            "label": label,
            "status": "completed",
        }

    yield {
        "type": "state",
        "status": "completed",
        "state": state,
    }


async def main():

    result = await run_graph_async(
        prompt="Create a futuristic AI startup website",
        selected_style="minimalism"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
