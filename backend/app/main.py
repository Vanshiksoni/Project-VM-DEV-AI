from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.services.rag import build_prompt
from backend.app.services.llm import generate_answer

app = FastAPI(
    title="DevAssist AI",
    description="Technical Documentation Assistant powered by RAG and Code Llama",
    version="1.0.0",
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The technical question to ask")
    top_k: Optional[int] = Field(default=2, ge=1, le=5)
    similarity_threshold: Optional[float] = Field(default=0.60, ge=0.0, le=1.0)


class SourceItem(BaseModel):
    filename: str
    section: str
    chunk_id: int
    similarity: float


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceItem]


@app.get("/")
def root():
    return {
        "name": "DevAssist AI",
        "status": "online",
        "endpoints": ["/health", "POST /ask", "GET /ask"]
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "DevAssist AI Backend"}


@app.post("/ask", response_model=AskResponse)
def ask_question(body: QuestionRequest):
    question_text = body.question.strip()
    if not question_text:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        prompt, sources, fallback = build_prompt(
            question_text,
            top_k=body.top_k,
            similarity_threshold=body.similarity_threshold
        )

        if fallback:
            answer = fallback
        else:
            answer = generate_answer(prompt)

        formatted_sources = [
            SourceItem(
                filename=source["filename"],
                section=source["section"],
                chunk_id=source["id"],
                similarity=round(source["score"], 4),
            )
            for source in sources
        ]

        return AskResponse(
            question=question_text,
            answer=answer,
            sources=formatted_sources,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


@app.get("/ask", response_model=AskResponse)
def ask_question_get(
    question: str = Query(..., min_length=1),
    top_k: int = Query(2, ge=1, le=5),
    similarity_threshold: float = Query(0.60, ge=0.0, le=1.0),
):
    """Backwards-compatible GET endpoint for asking questions."""
    req = QuestionRequest(
        question=question,
        top_k=top_k,
        similarity_threshold=similarity_threshold
    )
    return ask_question(req)

