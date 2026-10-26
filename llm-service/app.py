import json
import os
import re
import time
from typing import Optional, Generator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="DevAssist AI - LLM Inference Microservice",
    description="Dedicated microservice for LLM inference and real-time token streaming",
    version="2.0.0",
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "codellama:latest")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt to send to language model")
    context: Optional[str] = Field(default="", description="Optional RAG context")
    model: Optional[str] = Field(default=DEFAULT_MODEL, description="LLM model identifier")
    temperature: Optional[float] = Field(default=0.1, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=256, ge=16, le=2048)


def build_full_prompt(prompt: str, context: Optional[str]) -> str:
    if not context or not context.strip():
        return prompt
    return (
        "You are DevAssist AI, a strictly grounded technical documentation assistant.\n"
        "Answer the user query ONLY using the provided technical context.\n"
        "If the answer cannot be deduced directly from the context, state that the information is not available.\n\n"
        f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
        f"USER QUESTION: {prompt}\n\n"
        "Grounded Answer:"
    )


def extract_grounded_answer_from_prompt(prompt: str, context: Optional[str] = None) -> str:
    """
    Intelligently extracts and formats grounded answers directly from the documentation
    context for the specific question asked, when Ollama is offline or unreachable.
    """
    full_text = f"{context or ''}\n{prompt}"
    user_q = ""
    if "USER QUESTION:" in full_text:
        user_q = full_text.split("USER QUESTION:", 1)[1].strip().lower()
    elif "Answer the following question directly:" in full_text:
        user_q = full_text.split("Answer the following question directly:", 1)[1].strip().lower()
    else:
        user_q = prompt.strip().lower()

    context_text = ""
    if "DOCUMENTATION CONTEXT:" in full_text:
        parts = full_text.split("DOCUMENTATION CONTEXT:", 1)[1]
        context_text = parts.split("USER QUESTION:", 1)[0].strip()
    elif "--- CONTEXT ---" in full_text:
        parts = full_text.split("--- CONTEXT ---", 1)[1]
        context_text = parts.split("--- END CONTEXT ---", 1)[0].strip()
    else:
        context_text = full_text

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
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][2]

    # Fallback to sentences if no structured sections found
    cleaned = re.sub(r"#+\s*", "", context_text)
    sentences = [
        sen.strip()
        for sen in re.split(r"(?<=[.!?])\s+", cleaned)
        if len(sen.strip()) > 20 and not any(k in sen.lower() for k in ["you are devassist", "rules:", "documentation context:", "user question:"])
    ]
    if sentences:
        return " ".join(sentences[:2])

    return "The requested information is detailed in the indexed documentation sources."



@app.get("/")
def root():
    return {
        "service": "DevAssist AI - LLM Inference Microservice",
        "status": "online",
        "default_model": DEFAULT_MODEL,
        "ollama_url": OLLAMA_URL,
        "endpoints": ["/health", "POST /generate", "POST /stream"]
    }


@app.get("/health")
def health():
    ollama_ok = False
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=2.0)
        ollama_ok = (r.status_code == 200)
    except Exception:
        ollama_ok = False

    return {
        "status": "healthy" if ollama_ok else "degraded",
        "service": "llm-service",
        "ollama_online": ollama_ok,
        "ollama_endpoint": OLLAMA_URL,
        "default_model": DEFAULT_MODEL,
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    model = req.model or DEFAULT_MODEL
    full_prompt = build_full_prompt(req.prompt, req.context)

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "num_thread": 4,
            "num_ctx": 2048,
            "num_predict": req.max_tokens,
            "temperature": req.temperature,
        },
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=3.0)) as client:
            res = client.post(OLLAMA_URL, json=payload)
            res.raise_for_status()
            data = res.json()
            return {
                "model": model,
                "response": data.get("response", "").strip(),
                "total_duration": data.get("total_duration", 0),
            }
    except Exception as exc:
        fallback_ans = extract_grounded_answer_from_prompt(full_prompt, req.context)
        return {
            "model": model,
            "response": fallback_ans,
            "fallback": True,
            "detail": str(exc),
        }


def stream_generator(req: GenerateRequest) -> Generator[str, None, None]:
    model = req.model or DEFAULT_MODEL
    full_prompt = build_full_prompt(req.prompt, req.context)

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": True,
        "options": {
            "num_thread": 4,
            "num_ctx": 2048,
            "num_predict": req.max_tokens,
            "temperature": req.temperature,
        },
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=3.0)) as client:
            with client.stream("POST", OLLAMA_URL, json=payload) as res:
                res.raise_for_status()
                for line in res.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        if chunk.get("done", False):
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                    except Exception:
                        continue
    except Exception as exc:
        fallback_text = extract_grounded_answer_from_prompt(full_prompt, req.context)
        for word in fallback_text.split():
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            time.sleep(0.02)
        yield f"data: {json.dumps({'done': True, 'fallback': True})}\n\n"


@app.post("/stream")
def stream_endpoint(req: GenerateRequest):
    return StreamingResponse(
        stream_generator(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
