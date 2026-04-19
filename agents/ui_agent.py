import json
from ai_agentic_designer.agents.llm import llm
from ai_agentic_designer.mcp_server.tools.figma_tool import get_remote_figma_tools

tools, client = get_remote_figma_tools()


def generate_ui(prompt, plan):

    ui_prompt = f"""
    Generate UI layout.

    user request: 
    {prompt}
    Planner Output:
    {json.dumps(plan, indent=2)}
    You are the UI Design Agent.

    Your role:
    - Convert structured website specs into polished Figma designs.
    - Use tools instead of describing actions.
    - Prefer strong hierarchy, spacing, responsive layouts.
    - Reuse design system components when possible.
    - Build complete pages.

    STRICT RULES:
    - Use ONLY layout from planner
    - Do NOT add new sections
    - Do NOT remove sections
    - Output must exactly match planner layout

    Return JSON:
    {{
    "brand":"Nova AI",
    "style":"modern dark",
    "pages":[...],
    "tokens":{...},
    "sections":[...]
        }}
    """

    response = llm(ui_prompt)

    try:
        layout = json.loads(response)
    except:
        layout = {"layout": ["navbar", "hero"]}

    return layout
