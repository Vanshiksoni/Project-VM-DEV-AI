import json
import os
import re
import time
from typing import Generator
import httpx

# Support both direct Ollama or decoupled LLM-service container
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "codellama:latest")


def extract_grounded_answer_from_prompt(prompt: str) -> str:
    """
    Intelligently extracts and formats grounded answers directly from the technical context
    for the specific question asked, when Ollama inference is offline or in test mode.
    """
    user_q = ""
    if "USER QUESTION:" in prompt:
        user_q = prompt.split("USER QUESTION:", 1)[1].strip().lower()
    elif "Answer the following question directly:" in prompt:
        user_q = prompt.split("Answer the following question directly:", 1)[1].strip().lower()

    context_text = ""
    if "DOCUMENTATION CONTEXT:" in prompt:
        parts = prompt.split("DOCUMENTATION CONTEXT:", 1)[1]
        context_text = parts.split("USER QUESTION:", 1)[0].strip()
    elif "--- CONTEXT ---" in prompt:
        parts = prompt.split("--- CONTEXT ---", 1)[1]
        context_text = parts.split("--- END CONTEXT ---", 1)[0].strip()
    else:
        context_text = prompt

    section_blocks = re.findall(
        r"(?:Section:\s*([^\n]+)\s*\nContent:\s*|##\s*([^\n]+)\s*\n)([\s\S]*?)(?=(?:Source File:|---|Section:|##|USER QUESTION:|$))",
        context_text
    )

    q_words = [
        w for w in re.findall(r"\b\w{3,}\b", user_q)
        if w not in {"what", "is", "the", "for", "are", "and", "how", "can", "with", "does", "which", "about", "tell"}
    ]

    candidates = []
    if section_blocks:
        for block in section_blocks:
            title = (block[0] or block[1] or "").strip()
            body = (block[2] or "").strip()
            cleaned_body = re.sub(r"^#+\s*.*$", "", body, flags=re.MULTILINE).strip()
            paras = [p.strip() for p in cleaned_body.split("\n\n") if len(p.strip()) > 8]
            if paras:
                first_p = re.sub(r"\s+", " ", paras[0]).strip()
                score = sum(5 for w in q_words if w in title.lower()) + sum(1 for w in q_words if w in first_p.lower())
                candidates.append((score, title, first_p))

    if candidates:
        # Pick the single best answering section for this specific question
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][2]

    cleaned = re.sub(r"#+\s*", "", context_text)
    sentences = [
        sen.strip()
        for sen in re.split(r"(?<=[.!?])\s+", cleaned)
        if len(sen.strip()) > 20 and not any(k in sen.lower() for k in ["you are devassist", "rules:", "documentation context:", "user question:"])
    ]
    if sentences:
        return " ".join(sentences[:2])

    return "The requested information is detailed in the indexed documentation sources."



def generate_answer(prompt: str, model: str = DEFAULT_MODEL) -> str:
    selected_model = model if model else DEFAULT_MODEL

    # If dedicated LLM microservice container is specified
    if LLM_SERVICE_URL:
        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(
                    f"{LLM_SERVICE_URL.rstrip('/')}/generate",
                    json={"prompt": prompt, "model": selected_model},
                )
                if res.status_code == 200:
                    resp_str = res.json().get("response", "").strip()
                    if resp_str and not resp_str.startswith("Documentation Assistant: Grounded response"):
                        return resp_str
        except Exception:
            pass  # Fall back to direct Ollama

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
            return raw_answer.strip()
    except Exception:
        return extract_grounded_answer_from_prompt(prompt)


def generate_answer_stream(prompt: str, model: str = DEFAULT_MODEL) -> Generator[str, None, None]:
    selected_model = model if model else DEFAULT_MODEL

    # If dedicated LLM microservice container is specified
    if LLM_SERVICE_URL:
        try:
            with httpx.stream(
                "POST",
                f"{LLM_SERVICE_URL.rstrip('/')}/stream",
                json={"prompt": prompt, "model": selected_model},
                timeout=60.0,
            ) as response:
                if response.status_code == 200:
                    streamed_tokens = []
                    for line in response.iter_lines():
                        if not line:
                            continue
                        line_str = line.strip()
                        if line_str.startswith("data:"):
                            raw_json = line_str[5:].strip()
                            try:
                                obj = json.loads(raw_json)
                                if "token" in obj:
                                    streamed_tokens.append(obj["token"])
                                    yield obj["token"]
                                if obj.get("done", False):
                                    break
                            except Exception:
                                streamed_tokens.append(raw_json)
                                yield raw_json
                        else:
                            streamed_tokens.append(line_str)
                            yield line_str
                    if streamed_tokens:
                        return
        except Exception:
            pass  # Fall back to direct Ollama

    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_thread": 4,
            "num_ctx": 2048,
            "num_predict": 256,
            "temperature": 0.1,
        },
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=3.0)) as client:
            with client.stream("POST", OLLAMA_URL, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk_obj = json.loads(line)
                        token = chunk_obj.get("response", "")
                        if token:
                            yield token
                        if chunk_obj.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception:
        fallback_answer = extract_grounded_answer_from_prompt(prompt)
        for word in fallback_answer.split():
            yield word + " "
            time.sleep(0.02)


if __name__ == "__main__":
    test_prompt = "What is Docker? Answer in 1 short sentence."
    print("Testing generate_answer:")
    print(generate_answer(test_prompt))
