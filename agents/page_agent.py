import json
from ai_agentic_designer.agents.llm import llm


def generate_pages(prompt, plan):

  page_prompt = f"""
  
  Generate website pages based on the user request.
  Use the planner output pages list to generate ALL pages.
  Generate content for each page.

  Do NOT return a single page.

  user request: {prompt}
  Planner Output: {json.dumps(plan, indent=2)}
 


  Return JSON:
  {{
    "pages": [
      {{
        "name": "home",
        "content": "..."
      }},
      {{
        "name": "about", 
        "content": "..."
      }}
      ...
    ]
  }}
  """

  response = llm(page_prompt)

  try:
    pages = json.loads(response)
  except:
    pages = {"pages":["home"]}


  return pages 