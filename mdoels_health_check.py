import os
from dotenv import load_dotenv
import requests

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"


def test_openrouter(model: str):
    print(f"\n[TEST] OpenRouter model: {model}")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Model-Test",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with: OPENROUTER_OK"}
        ],
        "temperature": 0,
    }

    try:
        res = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        res.raise_for_status()
        output = res.json()["choices"][0]["message"]["content"]
        print("✅ SUCCESS:", output)
    except Exception as e:
        print("❌ FAILED:", str(e))


def test_ollama(model: str):
    print(f"\n[TEST] Ollama model: {model}")

    payload = {
        "model": model,
        "prompt": "Reply with: OLLAMA_OK",
        "stream": False,
    }

    try:
        res = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )
        res.raise_for_status()
        output = res.json().get("response", "")
        print("✅ SUCCESS:", output.strip())
    except Exception as e:
        print("❌ FAILED:", str(e))


if __name__ == "__main__":
    print("\n===== LLM MODEL HEALTH CHECK =====")

   
    test_openrouter("meta-llama/llama-3.1-8b-instruct")
    test_openrouter("mistralai/mistral-7b-instruct")

    # ---------- Local Ollama Models ----------
    test_ollama("llama3.2:latest")
    

    print("\n===== TEST COMPLETE =====")
