import json
from pathlib import Path
import pytest
import httpx

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"


def is_ollama_online():
    try:
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def mock_ollama_if_offline(monkeypatch):
    """
    If Ollama is not running (e.g., in GitHub Actions CI), automatically mock
    embed_query and generate_answer so tests pass cleanly without network dependencies.
    """
    if is_ollama_online():
        # Ollama is online, run real inference tests
        yield
        return

    # Ollama is offline (CI environment)
    print("\n[CI Environment Detected] Ollama is offline. Applying test mocks for CI pipeline.")

    # Load pre-computed embeddings for mock query matching
    embeddings_data = []
    if EMBEDDINGS_FILE.exists():
        embeddings_data = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))

    def mock_embed_query(question: str):
        q_lower = question.lower()

        # Map common query keywords to actual pre-computed chunk embeddings for accurate similarity scores in CI
        if "compose" in q_lower:
            # Chunk 5: Docker Compose
            for doc in embeddings_data:
                if doc["id"] == 5:
                    return doc["embedding"]
        elif "image" in q_lower:
            # Chunk 4: Docker Image
            for doc in embeddings_data:
                if doc["id"] == 4:
                    return doc["embedding"]
        elif "file" in q_lower:
            # Chunk 3: Dockerfile
            for doc in embeddings_data:
                if doc["id"] == 3:
                    return doc["embedding"]
        elif "stop" in q_lower:
            # Chunk 9: Stop a container
            for doc in embeddings_data:
                if doc["id"] == 9:
                    return doc["embedding"]
        elif "list" in q_lower or "ps" in q_lower:
            # Chunk 8: List running containers
            for doc in embeddings_data:
                if doc["id"] == 8:
                    return doc["embedding"]
        elif "docker" in q_lower:
            # Chunk 1: What is Docker?
            for doc in embeddings_data:
                if doc["id"] == 1:
                    return doc["embedding"]

        # Out-of-domain query mock embedding (all zeros, 0.0 similarity)
        return [0.0] * 768

    def mock_generate_answer(prompt: str):
        return "Docker is a platform for packaging and running applications in isolated containers."

    monkeypatch.setattr("backend.app.services.retriever.embed_query", mock_embed_query)
    monkeypatch.setattr("backend.app.services.rag.embed_query", mock_embed_query)
    monkeypatch.setattr("backend.app.services.llm.generate_answer", mock_generate_answer)
    monkeypatch.setattr("backend.app.main.generate_answer", mock_generate_answer)

    yield
