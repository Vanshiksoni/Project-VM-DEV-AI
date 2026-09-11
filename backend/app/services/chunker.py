from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"


def chunk_text(text, max_chars=1000):
    sections = []
    current_section = []

    for line in text.splitlines():
        # Start a new section whenever we encounter a Markdown heading
        if line.startswith("#") and current_section:
            sections.append("\n".join(current_section).strip())
            current_section = []

        current_section.append(line)

    if current_section:
        sections.append("\n".join(current_section).strip())

    chunks = []

    for section in sections:
        if not section:
            continue

        # Keep small logical sections together
        if len(section) <= max_chars:
            chunks.append(section)
            continue

        # Split very large sections without breaking words
        words = section.split()
        current = ""

        for word in words:
            if len(current) + len(word) + 1 > max_chars:
                if current:
                    chunks.append(current.strip())
                current = word
            else:
                current += " " + word

        if current:
            chunks.append(current.strip())

    return chunks


def load_and_chunk_documents():
    documents = []

    for file_path in DOCS_DIR.glob("*.md"):
        text = file_path.read_text(encoding="utf-8")

        chunks = chunk_text(text)

        for index, chunk in enumerate(chunks, start=1):
            documents.append(
                {
                    "filename": file_path.name,
                    "chunk_id": index,
                    "content": chunk,
                }
            )

    return documents


if __name__ == "__main__":
    documents = load_and_chunk_documents()

    print(f"Total chunks: {len(documents)}")

    for document in documents:
        print("\n" + "=" * 60)
        print(f"Source: {document['filename']}")
        print(f"Chunk: {document['chunk_id']}")
        print(document["content"])
