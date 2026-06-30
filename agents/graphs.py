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
    code_node
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
    "generation",
    generation_node
)

builder.add_node(
    "frame_extraction",
    frame_extraction_node
)

builder.add_node(
    "code",
    code_node
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
    "code"
)

builder.add_edge(
    "code",
    END
)



graph = builder.compile()



import asyncio


async def main():

    result = await graph.ainvoke(
        {
            "user_prompt":
            "Create a futuristic AI startup website",
            "selected_style": "modern"
        }
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())