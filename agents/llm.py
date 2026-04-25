import requests
import os
from dotenv import load_dotenv

load_dotenv()





def llm(prompt, SYSTEM_PROMPT=None):
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "qwen3:8b",
        "prompt": prompt,
        "system": SYSTEM_PROMPT or "",
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    response = requests.post(url, json=payload, timeout=420)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()




def llm_gemini(prompt, SYSTEM_PROMPT=None):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": os.getenv("GEMINI_API_KEY") 
    }
    messages = []
    if SYSTEM_PROMPT:
        messages.append({"role": "user", "parts": [{"text": SYSTEM_PROMPT}]})
        messages.append({"role": "model", "parts": [{"text": "Understood."}]})
    messages.append({"role": "user", "parts": [{"text": prompt}]})
    payload = {
        "contents": messages,
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}
    }
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]