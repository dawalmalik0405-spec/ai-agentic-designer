from ai_agentic_designer.agents.page_agent import generate_pages
from ai_agentic_designer.agents.design_agent import generate_design
from ai_agentic_designer.agents.ui_agent import generate_ui
from ai_agentic_designer.agents.planner_agent import planner
from ai_agentic_designer.agents.code_agent import generate_code
from ai_agentic_designer.agents.state import AgentState



def planner_node(state: AgentState):
    plan = planner(state['prompt'])
    print("Planner running")
    return {"plan": plan}

def page_node(state: AgentState):
    pages = generate_pages(state['prompt'], state['plan'])
    print("Page running")
    return {"pages": pages}


def ui_node(state: AgentState):
    ui_layout = generate_ui(
        state["prompt"],
        state["pages"],
        state["design"]
    )
    print("ui running")
    return {"ui": ui_layout}

def design_node(state: AgentState):
    design = generate_design(state["prompt"], state["plan"])
    print("theme running")
    return {"design": design}


def code_node(state: AgentState):
    code = generate_code(state=state)
    print("code agent running")
    return {"code": code}




