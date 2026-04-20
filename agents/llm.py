import requests
import json



def llm(prompt, SYSTEM_PROMPT=None):

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "qwen3:8b",
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
    }

    response = requests.post(url, json=payload)

    data = response.json()

    return data.get("response", "")
