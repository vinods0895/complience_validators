# llm_clients.py

import requests
from typing import Callable, Dict


OLLAMA_URL = "http://localhost:11434/api/generate"


def call_ollama(model: str, prompt: str, timeout: int = 120) -> str:
    """
    Low-level Ollama call.
    Always returns a string (never None).
    """
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("response", "") or ""


def ollama_client(model: str) -> Callable[[str], str]:
    """
    Factory that returns a callable LLM client.
    """
    def invoke(prompt: str) -> str:
        return call_ollama(model, prompt)
    return invoke


def disabled_client(reason: str) -> Callable[[str], str]:
    """
    Safe placeholder client.
    """
    def invoke(_: str) -> str:
        return f"LLM disabled: {reason}"
    return invoke



# REGISTER ALL LLMs HERE


llm_clients: Dict[str, Callable[[str], str]] = {

    #  Primary production model
    "ollama_llama3": ollama_client("llama3.2:latest"),

    #  Reasoning-heavy (slow but smart)
    "ollama_deepseek_r1": ollama_client("deepseek-r1:1.5b"),

    #  Lightweight / fast / cheap
    "ollama_gemma": ollama_client("gemma:270m"),

    #  Compatibility
    "or_mistral_7b": disabled_client(
        "OpenRouter disabled in this environment"
    ),
}
