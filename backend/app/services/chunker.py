from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"


def chunk_text(text: str, max_chars: int = 1000):
    """
    Chunks markdown text into meaningful semantic sections.
    Preserves section titles and filters out standalone heading-only chunks.
    Returns a list of dicts: [{"section": str, "content": str}]
    """
    lines = text.splitlines()
    sections = []
    current_title = "General"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        # Check for top-level or sub-level Markdown headings (# Heading, ## Section, ### Subsection)
        if stripped.startswith("#"):
            # Non-heading content accumulated so far?
            non_heading_content = [
                l for l in current_lines if l.strip() and not l.strip().startswith("#")
            ]

            if non_heading_content:
                content = "\n".join(current_lines).strip()
                sections.append({"section": current_title, "content": content})
                current_lines = []
            elif current_lines:
                # previous heading didn't have body text yet (e.g. ## Common Docker Commands before ### Build an image)
                # Keep accumulating under the updated title if needed
                pass

            heading_text = stripped.lstrip("#").strip()
            if heading_text:
                current_title = heading_text

            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        non_heading_content = [
            l for l in current_lines if l.strip() and not l.strip().startswith("#")
        ]
        if non_heading_content:
            content = "\n".join(current_lines).strip()
            sections.append({"section": current_title, "content": content})

    final_chunks = []
    for sec in sections:
        content = sec["content"].strip()

        if len(content) <= max_chars:
            final_chunks.append({"section": sec["section"], "content": content})
        else:
            words = content.split()
            current_chunk = ""
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_chars:
                    if current_chunk:
                        final_chunks.append(
                            {"section": sec["section"], "content": current_chunk.strip()}
                        )
                    current_chunk = word
                else:
                    current_chunk += " " + word
            if current_chunk.strip():
                final_chunks.append(
                    {"section": sec["section"], "content": current_chunk.strip()}
                )

    return final_chunks


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
                    "section": chunk["section"],
                    "content": chunk["content"],
                }
            )

    return documents


if __name__ == "__main__":
    documents = load_and_chunk_documents()
    print(f"Total chunks: {len(documents)}")

    for doc in documents:
        print("\n" + "=" * 60)
        print(f"Source: {doc['filename']} | Chunk ID: {doc['chunk_id']} | Section: {doc['section']}")
        print(doc["content"])

