import json
from pathlib import Path

from document_loader import load_documents
from chunker import chunk_text


INDEX_DIR = Path(__file__).resolve().parents[3] / "data"
INDEX_FILE = INDEX_DIR / "documents.json"


def build_index():
    INDEX_DIR.mkdir(exist_ok=True)

    documents = load_documents()
    index = []

    chunk_id = 1

    for document in documents:
        chunks = chunk_text(document["content"])

        for chunk in chunks:
            index.append(
                {
                    "id": chunk_id,
                    "filename": document["filename"],
                    "content": chunk,
                }
            )

            chunk_id += 1

    INDEX_FILE.write_text(
        json.dumps(index, indent=2),
        encoding="utf-8",
    )

    return index


if __name__ == "__main__":
    index = build_index()

    print(f"Indexed {len(index)} chunks.")
    print(f"Saved to: {INDEX_FILE}")
