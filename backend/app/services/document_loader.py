from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"


def load_documents():
    documents = []

    for file_path in DOCS_DIR.glob("*.md"):
        text = file_path.read_text(encoding="utf-8")

        documents.append(
            {
                "filename": file_path.name,
                "path": str(file_path),
                "content": text,
            }
        )

    return documents


if __name__ == "__main__":
    documents = load_documents()

    print(f"Found {len(documents)} document(s)\n")

    for document in documents:
        print(f"File: {document['filename']}")
        print(f"Characters: {len(document['content'])}")
        print("-" * 40)
