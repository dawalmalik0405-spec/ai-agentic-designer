from ai_agentic_designer.agents.page_agent import generate_pages
from ai_agentic_designer.agents.planner_agent import planner
from ai_agentic_designer.agents.state import AgentState
from ai_agentic_designer.agents.theme_agent import generate_theme
from ai_agentic_designer.agents.ui_agent import generate_ui
from ai_agentic_designer.mcp_server.tools.figma_tool import sync_site_spec_to_figma


def planner_node(state: AgentState):
    site_spec = planner(state["prompt"])
    print("Planner running")
    return {"site_spec": site_spec}


def page_node(state: AgentState):
    site_spec = generate_pages(state["site_spec"])
    print("Page running")
    return {"site_spec": site_spec}


def ui_node(state: AgentState):
    site_spec = generate_ui(state["site_spec"])
    print("UI running")
    return {"site_spec": site_spec}


def theme_node(state: AgentState):
    site_spec = generate_theme(state["site_spec"])
    print("Theme running")
    return {"site_spec": site_spec}


def figma_node(state: AgentState):
    figma_result = sync_site_spec_to_figma(state["site_spec"])
    print("Figma running")
    return {"figma_result": figma_result}
