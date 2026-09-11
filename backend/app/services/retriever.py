import json
import math
from pathlib import Path

import httpx


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"

OLLAMA_URL = "http://127.0.0.1:11434/api/embed"
MODEL = "nomic-embed-text"


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


def retrieve(question, top_k=2):
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

        results.append(
            {
                "id": document["id"],
                "filename": document["filename"],
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
    question = input("Ask a documentation question: ")

    results = retrieve(question)

    print("\nTop relevant chunks:\n")

    for result in results:
        print("=" * 60)
        print(f"Chunk ID: {result['id']}")
        print(f"Source: {result['filename']}")
        print(f"Similarity: {result['score']:.4f}")
        print()
        print(result["content"])
