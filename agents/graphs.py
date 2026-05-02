from langgraph.graph import END, StateGraph

try:
    from .state import AgentState
    from ..node.nodes import (
        code_node,
        image_node,
        planner_node,
        repair_node,
        review_node,
    )
except ImportError:
    from agents.state import AgentState
    from node.nodes import (
        code_node,
        image_node,
        planner_node,
        repair_node,
        review_node,
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

    workflow.add_node("plan", planner_node)
    workflow.add_node("image", image_node)
    workflow.add_node("code", code_node)
    workflow.add_node("review", review_node)
    workflow.add_node("repair", repair_node)

    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "image")
    workflow.add_edge("image", "code")
    workflow.add_edge("code", "review")
    workflow.add_conditional_edges("review", route_after_review, {"repair": "repair", END: END})
    workflow.add_edge("repair", "review")

    return workflow.compile()


def run_graph(prompt: str, selected_style: str = "minimalism"):
    graph = create_agent_graph()
    final_state = graph.invoke(
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


# if __name__ == "__main__":
#     result = run_graph("Create futuristic AI startup website")
#     print(result)
