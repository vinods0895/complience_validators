import os
import requests
from typing import Callable
from dotenv import load_dotenv

load_dotenv()

# =====================================================
# ENV
# =====================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# =====================================================
# RAW HTTP CLIENTS
# =====================================================

def call_openrouter(model: str, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Invoice-Compliance-POC",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_ollama(model: str, prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


# =====================================================
# LANGCHAIN WRAPPER (NO PAID MODELS)
# =====================================================

def langchain_wrapper(llm_callable: Callable[[str], str]) -> Callable[[str], str]:
    """
    Wraps any callable(prompt)->str into a LangChain-style runnable
    WITHOUT using paid models.
    """
    from langchain_core.runnables import RunnableLambda

    runnable = RunnableLambda(lambda prompt: llm_callable(prompt))

    def invoke(prompt: str) -> str:
        return runnable.invoke(prompt)

    return invoke


# =====================================================
# REGISTRY
# =====================================================

llm_clients = {
    # -------------------------
    # OpenRouter (FREE)
    # -------------------------
    "openrouter_free": langchain_wrapper(
        lambda prompt: call_openrouter(
            "mistralai/mistral-7b-instruct-v0.1",
            prompt,
        )
    ),

    # -------------------------
    # Ollama (LOCAL)
    # -------------------------
    "ollama_local": langchain_wrapper(
        lambda prompt: call_ollama(
            "llama3.2:latest",
            prompt,
        )
    ),
}
