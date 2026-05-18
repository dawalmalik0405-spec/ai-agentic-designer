import asyncio
import logging

from agents.code_agent import generate_code
from agents.planner_agent import planner
from agents.repair_agent import repair_project
from agents.review_agent import review_project
from agents.state import AgentState
from agents.research_agent import ResearchAgent
from agents.designing_agent import DesigningAgent, get_designing_agent

logger = logging.getLogger(__name__)


def planner_node(state: AgentState):
    try:
        selected_style = state.get("selected_style", "minimalism")
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
        }
    except Exception as exc:
        logger.exception("Planner node failed")
        errors = list(state.get("errors", []))
        errors.append(f"planner: {exc}")
        raise RuntimeError(f"Planner node failed: {exc}") from exc


def code_node(state: AgentState):
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
        }
    except Exception as exc:
        logger.exception("Code node failed")
        errors = list(state.get("errors", []))
        errors.append(f"code: {exc}")
        raise RuntimeError(f"Code node failed: {exc}") from exc


def review_node(state: AgentState):
    try:
        print("[agent] review: started", flush=True)
        review = review_project(state=state)
        issue_count = len(review.get("issues", []))
        print(f"[agent] review: completed ({issue_count} issues)", flush=True)
        logger.info("Review node completed")
        return {
            "review": review,
            "current_agent": "review",
            "is_complete": not review.get("needs_repair", False),
        }
    except Exception as exc:
        logger.exception("Review node failed")
        raise RuntimeError(f"Review node failed: {exc}") from exc


def repair_node(state: AgentState):
    try:
        print(
            f"[agent] repair: started (attempt {state.get('repair_count', 0) + 1})",
            flush=True,
        )
        result = repair_project(state=state)
        print("[agent] repair: completed", flush=True)
        logger.info("Repair node completed")
        return {
            "files": result["files"],
            "repair_count": result["repair_count"],
            "current_agent": "repair",
            "is_complete": False,
        }
    except Exception as exc:
        logger.exception("Repair node failed")
        raise RuntimeError(f"Repair node failed: {exc}") from exc


async def research_node(state: AgentState):
    try:
        print("[agent] research: started", flush=True)
        agent = ResearchAgent()
        inspiration = await agent.gather_inspiration(
            keyword=state.get("selected_style", "minimalism"),
            animation_goal=state.get("prompt", "")
        )
        print(
            f"[agent] research: completed, got {len(inspiration.get('ui_patterns', []))} patterns",
            flush=True,
        )
        return {
            "inspiration_data": inspiration,
        }
    except Exception as exc:
        logger.exception("Research node failed")
        raise RuntimeError(f"Research node failed: {exc}") from exc


async def design_node(state: AgentState):
    try:
        print("[agent] design: started", flush=True)
        agent = get_designing_agent()
        pages = state.get("pages", {}).get("pages", [])
        design_systems = {}
        animation_specs = {}
        page_templates = {}
        for page in pages:
            result = await agent.generate_for_page(page)
            design_systems[page.get("name")] = result.get("design_system")
            animation_specs[page.get("name")] = result.get("animation_spec")
            page_templates[page.get("name")] = result.get("page_template")
        print(f"[agent] design: completed for {len(pages)} pages", flush=True)
        return {
            "design_system": design_systems,
            "animation_spec": animation_specs,
            "page_templates": page_templates,
            "current_agent": "design",
        }
    except Exception as exc:
        logger.exception("Design node failed")
        raise RuntimeError(f"Design node failed: {exc}") from exc
