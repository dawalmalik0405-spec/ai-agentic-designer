import json

import requests

SYSTEM_PROMPT = """
You are an AI UI/UX design system that helps generate structured outputs
for building websites using multi-agent architecture.
"""

def llm(prompt, system_prompt=None):

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "qwen3:8b",
        "prompt": prompt,
        "system": system_prompt or SYSTEM_PROMPT,
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=45)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    try:
        data = response.json()
    except json.JSONDecodeError:
        return ""

    return data.get("response", "")
