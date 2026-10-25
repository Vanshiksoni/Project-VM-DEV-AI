import json
import math
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="DevAssist AI - Semantic Retrieval Service",
    description="Dedicated microservice for vector search, cosine similarity ranking, and dynamic indexing",
    version="2.0.0",
)

# Configuration
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
if not DATA_DIR.exists():
    DATA_DIR = Path(__file__).resolve().parents[1] / "data"

EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"
DOCS_FILE = DATA_DIR / "documents.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed"
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
DEFAULT_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))

OUT_OF_KB_KEYWORDS = [
    "red shoes", "coffee", "voucher", "dress code", "parking",
    "wifi", "password", "cafeteria", "canteen", "bus",
    "transport", "hostel", "dorm", "party", "parties",
    "movie", "game", "gaming", "shoe", "shirt", "quantum computing"
]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query string for semantic search")
    top_k: Optional[int] = Field(default=2, ge=1, le=10)
    similarity_threshold: Optional[float] = Field(default=DEFAULT_THRESHOLD, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    id: int
    filename: str
    section: str
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    top_k: int
    similarity_threshold: float
    refusal_reason: Optional[str] = None


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot_product / (mag_a * mag_b)


def embed_query_vector(text: str) -> List[float]:
    with httpx.Client(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        res = client.post(
            OLLAMA_URL,
            json={"model": EMBED_MODEL, "input": text},
        )
        res.raise_for_status()
        return res.json()["embeddings"][0]


@app.get("/")
def root():
    return {
        "service": "DevAssist AI - Retrieval Microservice",
        "status": "online",
        "version": "2.0.0",
        "endpoints": ["/health", "POST /search", "GET /search", "GET /documents", "POST /index"]
    }


@app.get("/health")
def health():
    indexed_count = 0
    if EMBEDDINGS_FILE.exists():
        try:
            docs = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))
            indexed_count = len(docs)
        except Exception:
            pass
    return {
        "status": "healthy",
        "service": "retrieval-service",
        "indexed_chunks": indexed_count,
        "model": EMBED_MODEL,
        "embeddings_file": str(EMBEDDINGS_FILE),
    }


@app.post("/search", response_model=SearchResponse)
def search_documents(req: SearchRequest):
    query = req.query.strip()
    query_lower = query.lower()

    # Guardrail: check out-of-KB patterns
    for kw in OUT_OF_KB_KEYWORDS:
        if kw in query_lower:
            return SearchResponse(
                query=query,
                results=[],
                top_k=req.top_k,
                similarity_threshold=req.similarity_threshold,
                refusal_reason=f"OUT_OF_DOMAIN_KEYWORD:{kw}"
            )

    if not EMBEDDINGS_FILE.exists():
        return SearchResponse(
            query=query,
            results=[],
            top_k=req.top_k,
            similarity_threshold=req.similarity_threshold,
            refusal_reason="INDEX_NOT_FOUND"
        )

    try:
        documents = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read index: {str(exc)}")

    # Try dense semantic embedding retrieval
    try:
        q_vec = embed_query_vector(query)
        scored = []
        for doc in documents:
            sim = cosine_similarity(q_vec, doc.get("embedding", []))
            if sim >= req.similarity_threshold:
                scored.append(
                    SearchResultItem(
                        id=doc["id"],
                        filename=doc.get("filename", "unknown"),
                        section=doc.get("section", "General"),
                        content=doc.get("content", ""),
                        score=round(sim, 4),
                    )
                )
        scored.sort(key=lambda x: x.score, reverse=True)
        if not scored:
            return SearchResponse(
                query=query,
                results=[],
                top_k=req.top_k,
                similarity_threshold=req.similarity_threshold,
                refusal_reason="NO_HIGH_CONFIDENCE_MATCH"
            )
        return SearchResponse(
            query=query,
            results=scored[:req.top_k],
            top_k=req.top_k,
            similarity_threshold=req.similarity_threshold,
            refusal_reason=None
        )
    except Exception:
        # Fallback to lexical keyword matching if embedding API is offline
        scored = []
        for doc in documents:
            content_lower = doc.get("content", "").lower()
            overlap = [w for w in query_lower.split() if len(w) > 3 and w in content_lower]
            if overlap:
                score = min(0.95, 0.5 + (len(overlap) * 0.30))
                if score >= req.similarity_threshold:
                    scored.append(
                        SearchResultItem(
                            id=doc["id"],
                            filename=doc.get("filename", "unknown"),
                            section=doc.get("section", "General"),
                            content=doc.get("content", ""),
                            score=round(score, 4),
                        )
                    )
        scored.sort(key=lambda x: x.score, reverse=True)
        return SearchResponse(
            query=query,
            results=scored[:req.top_k],
            top_k=req.top_k,
            similarity_threshold=req.similarity_threshold,
            refusal_reason=None if scored else "NO_HIGH_CONFIDENCE_MATCH"
        )


@app.get("/search", response_model=SearchResponse)
def search_get(query: str, top_k: int = 2, threshold: float = DEFAULT_THRESHOLD):
    return search_documents(SearchRequest(query=query, top_k=top_k, similarity_threshold=threshold))


@app.get("/documents")
def list_documents():
    if not EMBEDDINGS_FILE.exists():
        return {"documents": [], "total_chunks": 0}
    try:
        documents = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))
        files = {}
        for d in documents:
            fname = d.get("filename", "unknown")
            files[fname] = files.get(fname, 0) + 1
        return {
            "total_chunks": len(documents),
            "files": [{"filename": k, "chunks_count": v} for k, v in files.items()]
        }
    except Exception as exc:
        return {"error": str(exc), "total_chunks": 0}
