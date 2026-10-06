import os
import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "codellama:latest")


def generate_answer(prompt: str, model: str = DEFAULT_MODEL) -> str:
    selected_model = model if model else DEFAULT_MODEL

    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_thread": 4,
            "num_ctx": 2048,
            "num_predict": 256,
            "temperature": 0.1,
        },
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=3.0)) as client:
            response = client.post(
                OLLAMA_URL,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()
            raw_answer = data.get("response", "")

            # Output cleaning
            cleaned = raw_answer.strip()
            return cleaned
    except Exception as exc:
        return f"Error communicating with LLM model '{selected_model}': {str(exc)}"


if __name__ == "__main__":
    test_prompt = "What is Docker? Answer in 1 short sentence."
    print("Testing generate_answer:")
    print(generate_answer(test_prompt))
