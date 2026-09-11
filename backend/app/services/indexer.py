import json
from pathlib import Path

from backend.app.services.chunker import load_and_chunk_documents


INDEX_DIR = Path(__file__).resolve().parents[3] / "data"
INDEX_FILE = INDEX_DIR / "documents.json"


def build_index():
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

    return index


if __name__ == "__main__":
    index = build_index()

    print(f"Indexed {len(index)} chunks with section metadata.")
    print(f"Saved to: {INDEX_FILE}")

