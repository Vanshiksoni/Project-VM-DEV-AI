from locust import HttpUser, task, between
import random

SAMPLE_QUESTIONS = [
    "What is Docker?",
    "What is Docker Compose?",
    "What is a Docker image?",
    "What is a Dockerfile?",
    "What are common Docker commands?",
    "How do I list running containers in Docker?",
    "How do I stop a container in Docker?",
    "What is quantum computing?",
]


class DevAssistLoadUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(3)
    def ask_standard(self):
        q = random.choice(SAMPLE_QUESTIONS)
        self.client.post("/ask", json={
            "question": q,
            "model": "codellama:latest",
            "top_k": 2,
            "similarity_threshold": 0.60
        }, name="/ask [Standard]")

    @task(2)
    def ask_streaming(self):
        q = random.choice(SAMPLE_QUESTIONS)
        with self.client.post("/ask/stream", json={
            "question": q,
            "model": "codellama:latest",
            "top_k": 2,
            "similarity_threshold": 0.60
        }, stream=True, name="/ask/stream [SSE]") as response:
            for _ in response.iter_lines():
                pass

    @task(1)
    def check_system_metrics(self):
        self.client.get("/system/metrics", name="/system/metrics")

    @task(1)
    def check_health(self):
        self.client.get("/health", name="/health")
