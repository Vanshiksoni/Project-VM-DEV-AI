import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.retriever import cosine_similarity, retrieve


def test_cosine_similarity_identical():
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 3.0]
    score = cosine_similarity(vec_a, vec_b)
    assert abs(score - 1.0) < 1e-5


def test_cosine_similarity_orthogonal():
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    score = cosine_similarity(vec_a, vec_b)
    assert abs(score - 0.0) < 1e-5


def test_retrieve_in_domain():
    results = retrieve("What is a Docker image?", top_k=2, similarity_threshold=0.60)
    assert len(results) > 0
    assert results[0]["filename"] == "docker.md"
    assert results[0]["score"] >= 0.60
    assert "section" in results[0]


def test_retrieve_out_of_domain():
    results = retrieve("What is photosynthesis?", top_k=2, similarity_threshold=0.60)
    assert len(results) == 0
