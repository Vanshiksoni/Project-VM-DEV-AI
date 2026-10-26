import hashlib
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.app.services.chunker import load_and_chunk_documents
from backend.app.services.cache import clear_cache

BASE_DIR = Path(__file__).resolve().parents[3]
DOCS_DIR = BASE_DIR / "docs"
KB_DIR = BASE_DIR / "knowledge-base" / "documents"

INDEX_DIR = BASE_DIR / "data"
INDEX_FILE = INDEX_DIR / "documents.json"
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.json"

_LAST_KNOWN_SIGNATURE: Optional[str] = None
_LAST_SYNC_TIME: float = 0.0


def get_knowledge_base_signature() -> str:
    """
    Computes a deterministic hash of all document filenames, sizes, and mtimes
    in docs/ and knowledge-base/documents/.
    """
    files_info = []
    for d in (DOCS_DIR, KB_DIR):
        if d.exists():
            for p in sorted(list(d.glob("*.md")) + list(d.glob("*.txt"))):
                try:
                    stat = p.stat()
                    files_info.append(f"{p.name}:{stat.st_size}:{stat.st_mtime_ns}")
                except Exception:
                    pass
    raw = "|".join(files_info)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def has_knowledge_base_changed() -> bool:
    """
    Returns True if any file has been added, removed, or modified
    since the last sync, or if the embeddings index file is missing.
    """
    global _LAST_KNOWN_SIGNATURE
    if not EMBEDDINGS_FILE.exists() or not INDEX_FILE.exists():
        return True
    current_sig = get_knowledge_base_signature()
    return current_sig != _LAST_KNOWN_SIGNATURE


def build_index(sync_embeddings_now: bool = True, force_recompute_embeddings: bool = False) -> List[Dict[str, Any]]:
    """
    Loads all documents, chunks them, updates documents.json and embeddings.json,
    flushes the query cache, and updates the change detection signature.
    """
    global _LAST_KNOWN_SIGNATURE, _LAST_SYNC_TIME

    INDEX_DIR.mkdir(exist_ok=True)
    chunks = load_and_chunk_documents()
    index = []

    for chunk in chunks:
        index.append(
            {
                "id": chunk["chunk_id"],
                "filename": chunk["filename"],
                "section": chunk["section"],
                "content": chunk["content"],
            }
        )

    INDEX_FILE.write_text(
        json.dumps(index, indent=2),
        encoding="utf-8",
    )

    if sync_embeddings_now:
        # Import lazily to avoid circular imports
        from backend.app.services.embedder import sync_embeddings
        sync_embeddings(index, force_recompute=force_recompute_embeddings)

    # Invalidate cache so that stale query answers are never served
    clear_cache()

    _LAST_KNOWN_SIGNATURE = get_knowledge_base_signature()
    _LAST_SYNC_TIME = time.time()

    return index


def ensure_realtime_sync() -> bool:
    """
    Hot check called before query processing.
    If knowledge base files have changed on disk, automatically re-indexes them.
    Returns True if a real-time sync was executed.
    """
    if has_knowledge_base_changed():
        build_index(sync_embeddings_now=True, force_recompute_embeddings=False)
        return True
    return False


if __name__ == "__main__":
    index = build_index()
    print(f"Indexed {len(index)} chunks with section metadata.")
    print(f"Saved to: {INDEX_FILE}")
