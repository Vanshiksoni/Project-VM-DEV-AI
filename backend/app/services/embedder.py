import hashlib
import json
import math
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
INDEX_FILE = DATA_DIR / "documents.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed"
MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


def generate_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Produces a deterministic, unit-normalized 768-dimensional feature vector.
    Used when Ollama is offline or in CI environments so that new/updated chunks
    can immediately be queried via cosine similarity and keyword matching.
    """
    vec = [0.0] * dim
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vec[idx] += sign

    # Subword character n-grams for morphology
    for i in range(max(0, len(text) - 2)):
        tri = text[i:i+3].lower()
        h = int(hashlib.sha256(tri.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 4) & 1) else -1.0
        vec[idx] += 0.5 * sign

    mag = math.sqrt(sum(v * v for v in vec))
    if mag > 0:
        return [round(v / mag, 6) for v in vec]
    return [0.0] * dim


def create_embedding(client: httpx.Client, text: str) -> List[float]:
    response = client.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "input": text,
        },
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def sync_embeddings(chunks: Optional[List[Dict[str, Any]]] = None, force_recompute: bool = False) -> List[Dict[str, Any]]:
    """
    Synchronizes chunks with data/embeddings.json in real time.
    - Reuses existing embeddings for unchanged chunks to execute in milliseconds.
    - Embeds new/changed chunks with Ollama if online, or deterministic vectors if offline.
    """
    DATA_DIR.mkdir(exist_ok=True)

    if chunks is None:
        if not INDEX_FILE.exists():
            return []
        chunks = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    # Build cache of existing embeddings by content
    existing_map: Dict[str, List[float]] = {}
    if EMBEDDINGS_FILE.exists() and not force_recompute:
        try:
            old_docs = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))
            for doc in old_docs:
                c = doc.get("content", "").strip()
                emb = doc.get("embedding")
                if c and emb and len(emb) == 768:
                    existing_map[c] = emb
        except Exception:
            pass

    results = []
    # Test if Ollama is accessible with a short timeout
    ollama_ready = False
    try:
        with httpx.Client(timeout=httpx.Timeout(1.5, connect=1.0)) as probe:
            pr = probe.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            if pr.status_code == 200:
                ollama_ready = True
    except Exception:
        ollama_ready = False

    with httpx.Client(timeout=httpx.Timeout(15.0, connect=3.0)) as client:
        for chunk in chunks:
            content = chunk.get("content", "").strip()
            embedding = None

            if not force_recompute and content in existing_map:
                embedding = existing_map[content]
            elif ollama_ready:
                try:
                    embedding = create_embedding(client, chunk["content"])
                except Exception:
                    embedding = generate_fallback_embedding(chunk["content"])
            else:
                embedding = generate_fallback_embedding(chunk["content"])

            results.append({
                "id": chunk.get("id", chunk.get("chunk_id", len(results) + 1)),
                "filename": chunk.get("filename", "unknown"),
                "section": chunk.get("section", "General"),
                "content": chunk.get("content", ""),
                "embedding": embedding,
            })

    EMBEDDINGS_FILE.write_text(
        json.dumps(results, indent=None),
        encoding="utf-8",
    )
    return results


def create_embeddings():
    sync_embeddings(force_recompute=True)


if __name__ == "__main__":
    results = sync_embeddings(force_recompute=False)
    print(f"\nCompleted {len(results)} embeddings. Saved to: {EMBEDDINGS_FILE}")
