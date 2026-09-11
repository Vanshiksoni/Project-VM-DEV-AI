import httpx


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "codellama:7b-instruct"


def generate_answer(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_thread": 2,
            "num_ctx": 1024,
            "num_predict": 80,
        },
    }

    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            OLLAMA_URL,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        return data["response"]
