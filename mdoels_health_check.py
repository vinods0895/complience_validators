import os
import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

  
# CONFIG
  

OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"

TIMEOUT_OPENROUTER = 60
TIMEOUT_OLLAMA = 120


  
# OPENROUTER HEALTH CHECK
  

def test_openrouter(model: str) -> bool:
    print(f"\n[CHECK] OpenRouter → {model}")

    if not OPENROUTER_API_KEY:
        print("⚠️  SKIPPED: OPENROUTER_API_KEY not set")
        return False

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "LLM-Health-Check",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with exactly: OPENROUTER_OK"}
        ],
        "temperature": 0,
    }

    try:
        res = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=TIMEOUT_OPENROUTER,
        )
        res.raise_for_status()

        content = (
            res.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if "OPENROUTER_OK" in content:
            print("✅ SUCCESS:", content)
            return True

        print("⚠️  UNEXPECTED RESPONSE:", content)
        return False

    except requests.exceptions.HTTPError as e:
        print("❌ HTTP ERROR:", e.response.text)
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: OpenRouter took too long")
    except Exception as e:
        print("❌ FAILED:", str(e))

    return False


  
# OLLAMA HEALTH CHECK
  

def test_ollama(model: str) -> bool:
    print(f"\n[CHECK] Ollama → {model}")

    payload = {
        "model": model,
        "prompt": "Reply with exactly: OLLAMA_OK",
        "stream": False,
    }

    try:
        res = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT_OLLAMA,
        )
        res.raise_for_status()

        output = res.json().get("response", "").strip()

        if "OLLAMA_OK" in output:
            print("✅ SUCCESS:", output)
            return True

        print("⚠️  UNEXPECTED RESPONSE:", output)
        return False

    except requests.exceptions.ConnectionError:
        print("❌ Ollama not running on localhost:11434")
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: Ollama model too slow")
    except Exception as e:
        print("❌ FAILED:", str(e))

    return False


  
# MAIN
  

if __name__ == "__main__":
    print("\n================ LLM HEALTH CHECK ================")

    results = {}

    # -------- OpenRouter Models --------
    results["openrouter_llama_3_1"] = test_openrouter(
        "meta-llama/llama-3.1-8b-instruct"
    )

    results["openrouter_mistral_7b"] = test_openrouter(
        "mistralai/mistral-7b-instruct"
    )

    # -------- Local Ollama Models --------
    results["ollama_llama3"] = test_ollama("llama3.2:latest")
    results["ollama_deepseek_r1"] = test_ollama("deepseek-r1:1.5b")
    results["ollama_gemma"] = test_ollama("gemma:270m")

    # -------- Summary --------
    print("\n================ SUMMARY ================")
    for name, ok in results.items():
        status = "READY ✅" if ok else "UNAVAILABLE ❌"
        print(f"{name}: {status}")

    print("\n================ TEST COMPLETE ================")
