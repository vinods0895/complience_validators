import requests
from typing import Callable


def call_ollama(model: str, prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def simple_wrapper(fn: Callable[[str], str]) -> Callable[[str], str]:
    def invoke(prompt: str) -> str:
        return fn(prompt)
    return invoke


llm_clients = {
    "ollama_llama3": simple_wrapper(
        lambda prompt: call_ollama("llama3.2:latest", prompt)
    ),
    # kept for compatibility if needed later
    "or_mistral_7b": simple_wrapper(
        lambda prompt: "LLM disabled for openrouter in this run"
    ),
}
