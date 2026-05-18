from langgraph.graph import StateGraph

from agents.state import AgentState
from node.nodes import code_node, planner_node


def create_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("plan", planner_node)
    workflow.add_node("code", code_node)

    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "code")

    return workflow.compile()


async def run_graph_async(prompt: str, selected_style: str):
    graph = create_agent_graph()
    final_state = await graph.ainvoke(
        {
            "prompt": prompt,
            "selected_style": selected_style,
            "errors": [],
        },
        config={"recursion_limit": 80},
    )
    return final_state


def run_graph(prompt: str, selected_style: str):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
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
