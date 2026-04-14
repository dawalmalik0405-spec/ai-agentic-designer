import json
from ai_agentic_designer.agents.llm import llm


def generate_pages(prompt, plan):

  page_prompt = f"""
  
  Generate website pages based on the user request.

  user request: {prompt}
  Planner Output: {json.dumps(plan, indent=2)}
 


  Return JSON:
  {{
    "pages": [
      {{
        "name": "home",
        "content": "..."
      }},
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