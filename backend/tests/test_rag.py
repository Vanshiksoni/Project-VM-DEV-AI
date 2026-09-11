import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.rag import build_prompt, OUT_OF_DOMAIN_RESPONSE


def test_build_prompt_in_domain():
    prompt, sources, fallback = build_prompt("What is Docker?", top_k=2, similarity_threshold=0.60)
    assert fallback is None
    assert prompt is not None
    assert "DOCUMENTATION CONTEXT:" in prompt
    assert len(sources) > 0


def test_build_prompt_out_of_domain():
    prompt, sources, fallback = build_prompt("Who won the World Cup in 2022?", top_k=2, similarity_threshold=0.60)
    assert fallback == OUT_OF_DOMAIN_RESPONSE
    assert prompt is None
    assert len(sources) == 0
