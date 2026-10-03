from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DOCS_DIR = BASE_DIR / "docs"
KB_DIR = BASE_DIR / "knowledge-base" / "documents"


def load_documents():
    documents = []

    # Load from docs/ (*.md, *.txt)
    if DOCS_DIR.exists():
        for file_path in list(DOCS_DIR.glob("*.md")) + list(DOCS_DIR.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            documents.append({
                "filename": file_path.name,
                "path": str(file_path),
                "content": text,
            })

    # Load from knowledge-base/documents/ (*.md, *.txt)
    if KB_DIR.exists():
        for file_path in list(KB_DIR.glob("*.md")) + list(KB_DIR.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            documents.append({
                "filename": file_path.name,
                "path": str(file_path),
                "content": text,
            })

    return documents


if __name__ == "__main__":
    documents = load_documents()
    print(f"Found {len(documents)} document(s)\n")
    for document in documents:
        print(f"File: {document['filename']}")
        print(f"Characters: {len(document['content'])}")
        print("-" * 40)
