import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.rag import build_prompt
from backend.app.services.llm import generate_answer

test_suite = [
    {
        "id": 1,
        "question": "What is Docker?",
        "category": "In-domain Direct",
        "expected_source": "docker.md (Section: What is Docker?)",
        "should_answer": True,
    },
    {
        "id": 2,
        "question": "What is Docker Compose?",
        "category": "In-domain Direct",
        "expected_source": "docker.md (Section: Docker Compose)",
        "should_answer": True,
    },
    {
        "id": 3,
        "question": "What is a Docker image?",
        "category": "In-domain Direct",
        "expected_source": "docker.md (Section: Docker Image)",
        "should_answer": True,
    },
    {
        "id": 4,
        "question": "What is a Dockerfile?",
        "category": "In-domain Direct",
        "expected_source": "docker.md (Section: Dockerfile)",
        "should_answer": True,
    },
    {
        "id": 5,
        "question": "What are common Docker commands?",
        "category": "In-domain Section",
        "expected_source": "docker.md (Commands sections)",
        "should_answer": True,
    },
    {
        "id": 6,
        "question": "How do I list running containers in Docker?",
        "category": "In-domain Paraphrased",
        "expected_source": "docker.md (Section: List running containers)",
        "should_answer": True,
    },
    {
        "id": 7,
        "question": "How do I stop a container in Docker?",
        "category": "In-domain Paraphrased",
        "expected_source": "docker.md (Section: Stop a container)",
        "should_answer": True,
    },
    {
        "id": 8,
        "question": "What is quantum computing?",
        "category": "Out-of-domain Invalid",
        "expected_source": "None (Out-of-domain)",
        "should_answer": False,
    },
    {
        "id": 9,
        "question": "How does photosynthesis work?",
        "category": "Out-of-domain Invalid",
        "expected_source": "None (Out-of-domain)",
        "should_answer": False,
    },
    {
        "id": 10,
        "question": "Who is the president of the United States?",
        "category": "Out-of-domain Invalid",
        "expected_source": "None (Out-of-domain)",
        "should_answer": False,
    },
]


def run_evaluation():
    print("\n==================================================")
    print("RUNNING DEVASSIST AI WEEK 2 EVALUATION SUITE")
    print("==================================================\n", flush=True)

    results = []

    for item in test_suite:
        q = item["question"]
        print(f"[{item['id']}/10] Testing: '{q}' ({item['category']})", flush=True)
        prompt, sources, fallback = build_prompt(q, top_k=2, similarity_threshold=0.60)

        if fallback:
            answer = fallback
            top_source = "None"
            max_sim = 0.0
        else:
            top_source = f"{sources[0]['filename']} ({sources[0]['section']})"
            max_sim = sources[0]["score"]
            answer = generate_answer(prompt)

        if item["should_answer"]:
            passed = len(sources) > 0 and fallback is None and "couldn't find" not in answer.lower()
        else:
            passed = len(sources) == 0 and fallback is not None

        results.append({
            "id": item["id"],
            "question": q,
            "category": item["category"],
            "retrieved_source": top_source,
            "similarity": max_sim,
            "answer": answer,
            "passed": passed
        })

        print(f"   -> Max Sim: {max_sim:.4f} | Source: {top_source}", flush=True)
        print(f"   -> Answer: {answer[:100]}...", flush=True)
        print(f"   -> Result: {'PASS' if passed else 'FAIL'}\n", flush=True)

    print("==================================================")
    print("SUMMARY BENCHMARK REPORT")
    print("==================================================", flush=True)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"Passed: {passed_count}/{len(results)} ({passed_count/len(results)*100:.1f}%)\n", flush=True)

    print("| Question | Category | Top Source | Similarity | Answer Snippet | Status |")
    print("| --- | --- | --- | --- | --- | --- |")
    for r in results:
        status_icon = "PASS" if r["passed"] else "FAIL"
        clean_ans = r["answer"].replace("\n", " ")[:60]
        print(f"| {r['question']} | {r['category']} | {r['retrieved_source']} | {r['similarity']:.4f} | {clean_ans}... | {status_icon} |")

if __name__ == "__main__":
    run_evaluation()
