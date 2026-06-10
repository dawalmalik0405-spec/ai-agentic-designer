import logging

from agents.code_agent import generate_code
from agents.planner_agent import planner
from agents.research_agent import ResearchAgent
from agents.state import AgentState

logger = logging.getLogger(__name__)


async def planner_node(state: AgentState):
    try:
        selected_style = str(state.get("selected_style", "")).strip()
        if not selected_style:
            raise ValueError("selected_style is required")
        print(f"[agent] planner: started (style={selected_style})", flush=True)
        result = planner(state["prompt"], selected_style=selected_style)
        page_count = len(result.get("pages", {}).get("pages", []))
        print(f"[agent] planner: completed ({page_count} pages)", flush=True)
        logger.info("Planner node completed")
        return {
            "selected_style": selected_style,
            "plan": result["plan"],
            "design": result["design"],
            "pages": result["pages"],
            "ui": result["ui"],
            "is_complete": False,
        }
    except Exception as exc:
        logger.exception("Planner node failed")
        raise RuntimeError(f"Planner node failed: {exc}") from exc


async def code_node(state: AgentState):
    try:
        page_count = len(state.get("pages", {}).get("pages", []))
        print(f"[agent] code: started ({page_count} pages)", flush=True)
        result = generate_code(state=state)
        file_count = len(result.get("files", {}))
        print(f"[agent] code: completed ({file_count} files)", flush=True)
        logger.info("Code node completed")
        return {
            "files": result["files"],
            "current_agent": "code",
            "is_complete": True,
        }
    except Exception as exc:
        logger.exception("Code node failed")
        raise RuntimeError(f"Code node failed: {exc}") from exc


async def research_node(state: AgentState):
    try:
        print("[agent] research: started", flush=True)
        selected_style = str(state.get("selected_style", "")).strip()
        if not selected_style:
            raise ValueError("selected_style is required")

        agent = ResearchAgent()
        inspiration = await agent.gather_inspiration(
            prompt=state.get("prompt", ""),
            selected_style=selected_style,
            pages=state.get("pages", {}).get("pages", []),
        )
        reference_count = len(inspiration.get("references", []))
        print(f"[agent] research: completed ({reference_count} references)", flush=True)
        logger.info("Research node completed")
        return {
            "inspiration_data": inspiration,
            "current_agent": "research",
            "is_complete": False,
        }
    except Exception as exc:
        logger.exception("Research node failed")
        raise RuntimeError(f"Research node failed: {exc}") from exc
