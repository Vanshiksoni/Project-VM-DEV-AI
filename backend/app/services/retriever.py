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


def cosine_similarity(vector_a, vector_b):
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

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
    if not EMBEDDINGS_FILE.exists():
        return []

    documents = json.loads(
        EMBEDDINGS_FILE.read_text(encoding="utf-8")
    )

    query_embedding = embed_query(question)

    results = []

    for document in documents:
        score = cosine_similarity(
            query_embedding,
            document["embedding"],
        )

        if score >= similarity_threshold:
            results.append(
                {
                    "id": document["id"],
                    "filename": document["filename"],
                    "section": document.get("section", "General"),
                    "content": document["content"],
                    "score": score,
                }
            )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:top_k]


if __name__ == "__main__":
    test_questions = [
        "What is Docker?",
        "What is Docker Compose?",
        "What is quantum computing?",
    ]

    for q in test_questions:
        print(f"\nQuestion: {q}")
        matches = retrieve(q, top_k=2, similarity_threshold=0.60)
        print(f"Retrieved {len(matches)} relevant chunk(s):")
        for res in matches:
            print(f"  - [{res['filename']} | Chunk {res['id']} | {res['section']}] Similarity: {res['score']:.4f}")

