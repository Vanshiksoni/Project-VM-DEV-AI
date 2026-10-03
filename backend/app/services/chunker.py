from pathlib import Path
from backend.app.services.document_loader import load_documents


def chunk_text(text: str, max_chars: int = 1000):
    """
    Chunks text into meaningful semantic sections.
    Preserves section titles and filters out standalone heading-only chunks.
    Returns a list of dicts: [{"section": str, "content": str}]
    """
    lines = text.splitlines()
    sections = []
    current_title = "General"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        # Check for top-level or sub-level headings (# Heading, ## Section, ### Subsection)
        if stripped.startswith("#"):
            non_heading_content = [
                l for l in current_lines if l.strip() and not l.strip().startswith("#")
            ]

            if non_heading_content:
                content = "\n".join(current_lines).strip()
                sections.append({"section": current_title, "content": content})
                current_lines = []

            heading_text = stripped.lstrip("#").strip()
            if heading_text:
                current_title = heading_text

            current_lines.append(line)
        elif stripped and len(current_lines) == 0 and not stripped.startswith("#"):
            # If paragraph starts, use title or paragraph start as section
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({"section": current_title, "content": content})

    if not sections:
        sections.append({"section": "General", "content": text.strip()})

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
    documents = load_documents()
    all_chunks = []
    chunk_counter = 1

    for doc in documents:
        chunks = chunk_text(doc["content"])
        for chunk in chunks:
            all_chunks.append({
                "filename": doc["filename"],
                "chunk_id": chunk_counter,
                "section": chunk["section"],
                "content": chunk["content"],
            })
            chunk_counter += 1

    return all_chunks


if __name__ == "__main__":
    documents = load_and_chunk_documents()
    print(f"Total chunks across all documents: {len(documents)}")
    for doc in documents:
        print(f"[{doc['filename']} | Chunk ID: {doc['chunk_id']} | {doc['section']}]")
