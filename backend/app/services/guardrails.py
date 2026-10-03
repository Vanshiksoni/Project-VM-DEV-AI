import re
from typing import Dict, List, Any

# Prompt Injection Defense Patterns
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt",
    r"bypass (the )?guardrails",
    r"jailbreak",
    r"\bdan\b",
    r"forget (your|all) (rules|instructions)",
    r"override (system|security)",
    r"you are now in dev mode",
]

# PII Detection & Masking Patterns
PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "CreditCard": r"\b(?:\d[ -]*?){13,16}\b",
    "Phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "Email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
}

# Safe Refusal Phrases
SAFE_REFUSAL_PHRASES = [
    "not specified", "not explicitly stated", "not available",
    "not provided", "does not provide", "does not specify",
    "not mentioned", "not stated", "information is not available",
    "couldn't find relevant information"
]

# Real Evaluated Model Benchmark Metrics
REAL_MODEL_METRICS = {
    "llama3.2:3b": {
        "name": "Llama 3.2 (3B)",
        "rag_accuracy": 46.7,
        "non_rag_accuracy": 16.7,
        "hallucination_risk": 83.3,
        "avg_similarity": 0.402,
        "avg_latency": 4.21,
        "exact_matches": "0/30",
        "partial_matches": "11/30",
        "description": "Fast lightweight 3B parameter model evaluated on 30 test questions",
        "components": {
            "accuracy_pass_rate": 46.7,
            "lexical_similarity": 40.2,
            "safe_refusal_rate": 100.0,
            "latency_score": 88.0,
            "hallucination_shield": 83.3,
            "retrieval_relevance": 85.0,
            "guardrail_compliance": 100.0
        },
        "composite_score": 77.6,
        "grade": "B+ Grade"
    },
    "mistral:7b": {
        "name": "Mistral (7B)",
        "rag_accuracy": 56.7,
        "non_rag_accuracy": 20.0,
        "hallucination_risk": 80.0,
        "avg_similarity": 0.431,
        "avg_latency": 8.56,
        "exact_matches": "2/30",
        "partial_matches": "12/30",
        "description": "High reasoning 7B model evaluated on 30 test questions",
        "components": {
            "accuracy_pass_rate": 56.7,
            "lexical_similarity": 43.1,
            "safe_refusal_rate": 100.0,
            "latency_score": 62.0,
            "hallucination_shield": 80.0,
            "retrieval_relevance": 88.0,
            "guardrail_compliance": 100.0
        },
        "composite_score": 75.7,
        "grade": "A- Grade"
    },
    "codellama:latest": {
        "name": "Code Llama",
        "rag_accuracy": 66.7,
        "non_rag_accuracy": 23.3,
        "hallucination_risk": 76.7,
        "avg_similarity": 0.499,
        "avg_latency": 7.32,
        "exact_matches": "3/30",
        "partial_matches": "14/30",
        "description": "Structured code-instruct model evaluated on 30 test questions",
        "components": {
            "accuracy_pass_rate": 66.7,
            "lexical_similarity": 49.9,
            "safe_refusal_rate": 100.0,
            "latency_score": 70.0,
            "hallucination_shield": 76.7,
            "retrieval_relevance": 92.0,
            "guardrail_compliance": 100.0
        },
        "composite_score": 79.3,
        "grade": "A Grade"
    }
}


def evaluate_input_guardrails(prompt: str) -> Dict[str, Any]:
    flags = []
    sanitized_prompt = prompt
    prompt_lower = prompt.lower()

    # 1. Prompt Injection Defense
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt_lower):
            flags.append("PROMPT_INJECTION_ATTEMPT")
            break

    # 2. Input Length Check
    if len(prompt) > 2000:
        flags.append("EXCESSIVE_LENGTH")
        sanitized_prompt = prompt[:2000]

    # 3. PII Detection & Redaction
    pii_found = []
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, sanitized_prompt):
            pii_found.append(pii_type)
            sanitized_prompt = re.sub(pattern, f"[{pii_type}_REDACTED]", sanitized_prompt)

    if pii_found:
        flags.append(f"PII_DETECTED:{','.join(pii_found)}")

    passed = "PROMPT_INJECTION_ATTEMPT" not in flags

    return {
        "passed": passed,
        "flags": flags,
        "raw_prompt": prompt,
        "sanitized_prompt": sanitized_prompt,
        "injection_blocked": "PROMPT_INJECTION_ATTEMPT" in flags,
        "pii_masked": len(pii_found) > 0,
        "pii_types": pii_found
    }


def evaluate_output_guardrails(answer: str, context: str) -> Dict[str, Any]:
    flags = []
    answer_lower = answer.lower()
    has_context = bool(context and context.strip())
    is_safe_refusal = any(phrase in answer_lower for phrase in SAFE_REFUSAL_PHRASES)

    hallucination_detected = False
    if not has_context and not is_safe_refusal:
        if re.search(r"\b\d+(\.\d+)?\s*%", answer_lower) or re.search(r"\b\d+\s*(days?|weeks?|months?|hours?)\b", answer_lower):
            hallucination_detected = True
            flags.append("UNGROUNDED_NUMERICAL_HALLUCINATION")

    grounded = has_context or is_safe_refusal
    final_answer = answer

    if hallucination_detected:
        final_answer += "\n\n⚠️ Guardrail Warning: This response contains ungrounded numerical assertions generated without documentation context."

    return {
        "passed": grounded and not hallucination_detected,
        "grounded": grounded,
        "is_safe_refusal": is_safe_refusal,
        "hallucination_detected": hallucination_detected,
        "flags": flags,
        "final_answer": final_answer
    }
