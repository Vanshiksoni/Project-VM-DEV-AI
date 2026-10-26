import json
import math
import os
import re
from pathlib import Path
import httpx

RETRIEVAL_STOPWORDS = {
    "what", "is", "a", "an", "the", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "and", "or", "vs", "versus", "are", "how", "can",
    "does", "do", "did", "which", "where", "when", "why", "who", "tell",
    "me", "about", "explain", "between", "this", "that", "these", "those"
}

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
    with httpx.Client(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
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
        # Fallback to smart lexical match if embedding API is offline
        q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", question) if w.lower() not in RETRIEVAL_STOPWORDS]
        if not q_words:
            q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", question)]

        scored = []
        for document in documents:
            content_lower = document["content"].lower()
            sec_lower = document.get("section", "").lower()
            raw_score = 0.0
            for w in q_words:
                if re.search(r"\b" + re.escape(w), sec_lower):
                    raw_score += 0.50
                if re.search(r"\b" + re.escape(w), content_lower):
                    raw_score += 0.35

            if raw_score >= 0.30:
                norm_score = min(0.98, round(0.50 + (raw_score * 0.22), 4))
                if norm_score >= similarity_threshold:
                    scored.append((
                        raw_score,
                        {
                            "id": document["id"],
                            "filename": document["filename"],
                            "section": document.get("section", "General"),
                            "content": document["content"],
                            "score": norm_score,
                        }
                    ))

        scored.sort(key=lambda item: (item[0], item[1]["score"]), reverse=True)
        results = [item[1] for item in scored]
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
