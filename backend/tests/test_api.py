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
    assert "couldn't find" in data["answer"].lower()
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
