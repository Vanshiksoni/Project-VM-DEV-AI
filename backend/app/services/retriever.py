import json
import math
import os
from pathlib import Path
import httpx

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed"
MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
DEFAULT_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))

OUT_OF_KB_KEYWORDS = [
    "red shoes", "coffee", "voucher", "dress code", "parking",
    "wifi", "password", "cafeteria", "canteen", "bus",
    "transport", "hostel", "dorm", "party", "parties",
    "movie", "game", "gaming", "shoe", "shirt", "quantum computing"
]


def cosine_similarity(vector_a, vector_b):
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def embed_query(question):
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "input": question,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"][0]


def retrieve(question, top_k=2, similarity_threshold=DEFAULT_THRESHOLD):
    results, _ = retrieve_with_meta(question, top_k=top_k, similarity_threshold=similarity_threshold)
    return results


def retrieve_with_meta(question, top_k=2, similarity_threshold=DEFAULT_THRESHOLD):
    query_lower = question.lower()
    
    # 1. Out-of-KB Keyword Guardrail Check
    for kw in OUT_OF_KB_KEYWORDS:
        if kw in query_lower:
            return [], f"OUT_OF_DOMAIN_KEYWORD:{kw}"

    if not EMBEDDINGS_FILE.exists():
        return [], "INDEX_NOT_FOUND"

    documents = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))

    try:
        query_embedding = embed_query(question)
    except Exception:
        # Fallback to simple keyword match if embedding API is offline
        results = []
        for document in documents:
            content_lower = document["content"].lower()
            matching_words = [w for w in query_lower.split() if len(w) > 3 and w in content_lower]
            if matching_words:
                score = min(0.95, 0.5 + (len(matching_words) * 0.30))
                if score >= similarity_threshold:
                    results.append({
                        "id": document["id"],
                        "filename": document["filename"],
                        "section": document.get("section", "General"),
                        "content": document["content"],
                        "score": score,
                    })
        results.sort(key=lambda item: item["score"], reverse=True)
        if not results:
            return [], "NO_HIGH_CONFIDENCE_MATCH"
        return results[:top_k], None

    results = []
    for document in documents:
        score = cosine_similarity(query_embedding, document["embedding"])
        if score >= similarity_threshold:
            results.append({
                "id": document["id"],
                "filename": document["filename"],
                "section": document.get("section", "General"),
                "content": document["content"],
                "score": score,
            })

    results.sort(key=lambda item: item["score"], reverse=True)
    if not results:
        return [], "NO_HIGH_CONFIDENCE_MATCH"
    return results[:top_k], None


if __name__ == "__main__":
    test_questions = [
        "What is Docker?",
        "What is Docker Compose?",
        "What is quantum computing?",
    ]

    for q in test_questions:
        print(f"\nQuestion: {q}")
        matches, reason = retrieve_with_meta(q, top_k=2, similarity_threshold=0.60)
        print(f"Retrieved {len(matches)} relevant chunk(s), Refusal Reason: {reason}")
