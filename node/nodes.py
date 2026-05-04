import logging

try:
    from ..agents.code_agent import generate_code
    from ..agents.image_agent import generate_images
    from ..agents.planner_agent import planner
    from ..agents.repair_agent import repair_project
    from ..agents.review_agent import review_project
    from ..agents.state import AgentState
except ImportError:
    from agents.code_agent import generate_code
    from agents.image_agent import generate_images
    from agents.planner_agent import planner
    from agents.repair_agent import repair_project
    from agents.review_agent import review_project
    from agents.state import AgentState


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
            "current_agent": "planner",
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


def image_node(state: AgentState):
    try:
        print("[agent] image: started", flush=True)
        result = generate_images(state=state)
        image_count = len(result.get("images", {}).get("pages", {}))
        print(f"[agent] image: completed ({image_count} pages)", flush=True)
        logger.info("Image node completed")
        return {
            "images": result["images"],
            "current_agent": "image",
        }
    except Exception as exc:
        logger.exception("Image node failed")
        raise RuntimeError(f"Image node failed: {exc}") from exc


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
