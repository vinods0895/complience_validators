import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"


# -------------------------
# OpenRouter Client
# -------------------------
def call_openrouter(model: str, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Invoice-Extraction-POC",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# -------------------------
# Ollama Client
# -------------------------
def call_ollama(model: str, prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json().get("response", "")


# -------------------------
# LLM Registry
# -------------------------
llm_clients = {
    # ✅ Best free OpenRouter model for extraction
    "openrouter_free": lambda prompt: call_openrouter(
        "mistralai/mistral-7b-instruct-v0.1",
        prompt
    ),

    # ✅ Lightweight local Ollama model
    "ollama_local": lambda prompt: call_ollama(
        "llama3.2:latest",
        prompt
    ),
}
