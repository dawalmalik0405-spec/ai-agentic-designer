import json
from langchain.tools import tool 
from agents.ui_agent import llm  # import your llm function


@tool
def generate_pages(prompt: str):
    """
    Generate website pages based on user prompt
    """

    page_prompt = f"""
    Based on the following website description, generate a list of pages.

    User Request:
    {prompt}

    Return JSON format:
    {{
        "pages": ["home", "about", "contact"]
    }}
    """

    response = llm(page_prompt)

    try:
        pages = json.loads(response)
    except:
        pages = {"pages": ["home"]}

    return pages