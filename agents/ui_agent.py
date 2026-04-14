import json
from ai_agentic_designer.agents.llm import llm


def generate_ui(prompt, plan):

    ui_prompt = f"""
    Generate UI layout sections.

    User Request:
    {prompt}
    planner request:{plan}

    Return JSON:
    {{
      "layout": ["navbar", "hero", "features", "footer"]
    }}
    """

    response = llm(ui_prompt)

    try:
        layout = json.loads(response)
    except:
        layout = {"layout": ["navbar", "hero"]}

    return layout