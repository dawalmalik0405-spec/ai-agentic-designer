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
    motion_node,          
)

import asyncio
import os


CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
GENERATED_SITE_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_site"
)







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
    "motion",
    motion_node
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
    "motion"
)

builder.add_edge(
    "motion",
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
        "motion_output": None,
        "generated_asset_output": None,
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

    result = await graph.ainvoke(state)

    return result







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
