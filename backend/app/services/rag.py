from backend.app.services.retriever import retrieve_with_meta, DEFAULT_THRESHOLD

OUT_OF_DOMAIN_RESPONSE = "I couldn't find relevant information in the indexed documentation."


def generate_guardrail_block_message(reason: str, question: str) -> str:
    if reason and reason.startswith("OUT_OF_DOMAIN_KEYWORD:"):
        kw = reason.split(":", 1)[1]
        return (
            f"🛡️ Guardrail Intervention: Out-of-Scope Query Blocked\n\n"
            f"• Reason: Topic keyword '{kw}' is outside system knowledge boundaries.\n"
            f"• Guardrail Enforcement: DevAssist AI strictly restricts answers to indexed Docker technical documentation "
            f"and official Academic Policy records to prevent ungrounded responses."
        )
    elif reason == "NO_HIGH_CONFIDENCE_MATCH":
        return (
            f"🚫 Guardrail Intervention: Low-Confidence Retrieval Halted\n\n"
            f"• Reason: No documentation chunks matched your query with similarity score >= 0.60.\n"
            f"• Guardrail Enforcement: Answer generation was halted by the Zero-Hallucination Guardrail "
            f"rather than returning unverified or fabricated claims."
        )
    else:
        return (
            f"🛡️ Guardrail Intervention Notice\n\n"
            f"• Reason: The requested query could not be verified against the indexed knowledge base.\n"
            f"• Guardrail Enforcement: Generation halted to enforce strict technical documentation grounding."
        )


def build_prompt(question, top_k=2, similarity_threshold=DEFAULT_THRESHOLD):
    results, refusal_reason = retrieve_with_meta(question, top_k=top_k, similarity_threshold=similarity_threshold)

    if not results:
        block_msg = generate_guardrail_block_message(refusal_reason, question)
        return None, [], block_msg

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
- If the documentation does not contain enough information, state that the information is not present.
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
            print(f"FALLBACK RESPONSE:\n{fallback}")
        else:
            print(f"PROMPT GENERATED ({len(sources)} sources):")
            print(prompt[:300] + "...")
