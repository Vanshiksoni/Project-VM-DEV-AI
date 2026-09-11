from backend.app.services.retriever import retrieve, DEFAULT_THRESHOLD

OUT_OF_DOMAIN_RESPONSE = "I couldn't find relevant information in the indexed documentation."


def build_prompt(question, top_k=2, similarity_threshold=DEFAULT_THRESHOLD):
    results = retrieve(question, top_k=top_k, similarity_threshold=similarity_threshold)

    if not results:
        return None, [], OUT_OF_DOMAIN_RESPONSE

    context_parts = []
    for result in results:
        context_parts.append(
            f"Source File: {result['filename']}\n"
            f"Section: {result['section']}\n"
            f"Content:\n{result['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are DevAssist AI, a technical documentation assistant.

Answer the user's question using ONLY the provided documentation context.

Rules:
- Use the documentation as the primary source.
- Do not invent information that is not supported by the documentation.
- If the documentation does not contain enough information, say "{OUT_OF_DOMAIN_RESPONSE}".
- Give a clear, direct, and concise technical answer without unnecessary filler.

DOCUMENTATION CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    return prompt, results, None


if __name__ == "__main__":
    for q in ["What is Docker?", "What is quantum computing?"]:
        print("\n" + "=" * 60)
        print(f"QUESTION: {q}")
        prompt, sources, fallback = build_prompt(q)
        if fallback:
            print(f"FALLBACK RESPONSE: {fallback}")
        else:
            print(f"PROMPT GENERATED ({len(sources)} sources):")
            print(prompt[:300] + "...")

