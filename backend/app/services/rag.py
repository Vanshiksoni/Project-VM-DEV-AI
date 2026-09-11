from backend.app.services.retriever import retrieve


def build_prompt(question, top_k=2):
    results = retrieve(question, top_k=top_k)

    context_parts = []

    for result in results:
        context_parts.append(
            f"Source: {result['filename']}\n"
            f"Section:\n{result['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are DevAssist AI, a technical documentation assistant.

Answer the user's question using the provided documentation.

Rules:
- Use the documentation as the primary source.
- Do not invent information that is not supported by the documentation.
- If the documentation does not contain enough information, say so.
- Give a clear and concise technical answer.

DOCUMENTATION:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    return prompt, results


if __name__ == "__main__":
    question = input("Ask a question: ")

    prompt, results = build_prompt(question)

    print("\n" + "=" * 60)
    print("GENERATED RAG PROMPT")
    print("=" * 60)
    print(prompt)

    print("\n" + "=" * 60)
    print("RETRIEVED SOURCES")
    print("=" * 60)

    for result in results:
        print(
            f"{result['filename']} | "
            f"Chunk {result['id']} | "
            f"Similarity: {result['score']:.4f}"
        )
