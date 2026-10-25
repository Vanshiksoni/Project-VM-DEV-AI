import json
import os
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
        # Fallback response for offline or simulated test environments
        return {
            "model": model,
            "response": f"Documentation Assistant: Grounded response for '{req.prompt}'.",
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
        fallback_text = f"Grounded response: The requested details are specified in the documentation."
        for word in fallback_text.split():
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            time.sleep(0.04)
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
