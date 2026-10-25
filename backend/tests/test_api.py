import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_post_ask_valid():
    response = client.post("/ask", json={"question": "What is Docker Compose?"})
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is Docker Compose?"
    assert "Docker Compose" in data["answer"] or len(data["sources"]) > 0
    assert len(data["sources"]) > 0
    assert data["sources"][0]["filename"] == "docker.md"
    assert data["sources"][0]["section"] == "Docker Compose"


def test_post_ask_out_of_domain():
    response = client.post("/ask", json={"question": "What is quantum computing?"})
    assert response.status_code == 200
    data = response.json()
    assert "guardrail intervention" in data["answer"].lower() or "blocked" in data["answer"].lower()
    assert len(data["sources"]) == 0


def test_post_ask_empty_question():
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400


def test_get_ask_backwards_compatible():
    response = client.get("/ask?question=What%20is%20a%20Dockerfile%3F")
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is a Dockerfile?"
    assert len(data["sources"]) > 0


def test_system_metrics_endpoint():
    response = client.get("/system/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "cache" in data
    assert "uptime_seconds" in data
    assert "active_threads" in data


def test_documents_endpoint():
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert "total_chunks" in data
    assert data["total_chunks"] >= 0


def test_documents_reindex_endpoint():
    response = client.post("/documents/reindex")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_indexed"] > 0


def test_ask_stream_endpoint():
    response = client.post("/ask/stream", json={"question": "What is Docker?"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "event: step" in text or "event: token" in text or "event: done" in text

