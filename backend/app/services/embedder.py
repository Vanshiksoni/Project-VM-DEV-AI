import json
import os
from pathlib import Path

import httpx


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
INDEX_FILE = DATA_DIR / "documents.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed"
MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


def create_embedding(client, text):
    response = client.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "input": text,
        },
    )

    response.raise_for_status()

    return response.json()["embeddings"][0]


def create_embeddings():
    documents = json.loads(
        INDEX_FILE.read_text(encoding="utf-8")
    )

    results = []

    with httpx.Client(timeout=120.0) as client:
        for document in documents:
            print(
                f"Embedding chunk {document['id']} "
                f"of {len(documents)}..."
            )

            embedding = create_embedding(
                client,
                document["content"],
            )

            results.append(
                {
                    "id": document["id"],
                    "filename": document["filename"],
                    "section": document.get("section", "General"),
                    "content": document["content"],
                    "embedding": embedding,
                }
            )

    EMBEDDINGS_FILE.write_text(
        json.dumps(results),
        encoding="utf-8",
    )

    print(
        f"\nCompleted {len(results)} embeddings. Saved to: {EMBEDDINGS_FILE}"
    )


if __name__ == "__main__":
    create_embeddings()

