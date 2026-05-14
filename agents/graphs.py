from langgraph.graph import END, StateGraph

from agents.state import AgentState
from node.nodes import (
    code_node,
    planner_node,
    repair_node,
    review_node,
    research_node,
    design_node,
)


MAX_REPAIR_ATTEMPTS = 2


def route_after_review(state: AgentState):
    review = state.get("review", {})
    needs_repair = review.get("needs_repair", False)

    if not needs_repair:
        return END

    if state.get("repair_count", 0) >= MAX_REPAIR_ATTEMPTS:
        return END

    return "repair"


def create_agent_graph():
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("plan", planner_node)
    workflow.add_node("research", research_node)
    workflow.add_node("design", design_node)
    workflow.add_node("code", code_node)
    workflow.add_node("review", review_node)
    workflow.add_node("repair", repair_node)

    # Set entry points for parallel execution
    workflow.set_entry_point("plan")
    workflow.set_entry_point("research")  # research and plan run concurrently

    # Design node waits for both plan and research
    workflow.add_edge("plan", "design")
    workflow.add_edge("research", "design")

    # After design, proceed to code
    workflow.add_edge("design", "code")

    # After code complete, proceed to review
    workflow.add_edge("code", "review")

    # Conditional repair loop
    workflow.add_conditional_edges("review", route_after_review, {"repair": "repair", END: END})
    workflow.add_edge("repair", "review")

    return workflow.compile()


async def run_graph_async(prompt: str, selected_style: str = "minimalism"):
    """Async version for agents that need async execution."""
    graph = create_agent_graph()
    final_state = await graph.ainvoke(
        {
            "prompt": prompt,
            "selected_style": selected_style,
            "errors": [],
            "repair_count": 0,
            "is_complete": False,
        },
        config={"recursion_limit": 80},
    )
    return final_state


def run_graph(prompt: str, selected_style: str = "minimalism"):
    """Sync wrapper for backward compatibility."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, create a new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, run_graph_async(prompt, selected_style))
                return future.result()
        else:
            return asyncio.run(run_graph_async(prompt, selected_style))
    except RuntimeError:
        return asyncio.run(run_graph_async(prompt, selected_style))


if __name__ == "__main__":
    result = run_graph("Create futuristic AI startup website with Glassmorphism style")
    print(result)
