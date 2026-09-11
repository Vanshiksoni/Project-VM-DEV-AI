# DevAssist AI

DevAssist AI is an intelligent, high-accuracy Technical Documentation Assistant powered by Retrieval-Augmented Generation (RAG) and local LLM inference via Ollama.

DevAssist AI ensures **grounded, zero-hallucination answers** by retrieving indexed technical documentation chunks and strictly restricting language model output to verified context.

---

## 🌟 Key Features

- **Strict Groundedness**: Returns zero hallucinated answers by using a cosine similarity threshold (`0.60`).
- **Out-of-Domain Rejection**: Gracefully falls back to *"I couldn't find relevant information in the indexed documentation."* when queries fall outside the documentation scope.
- **Section-Aware Semantic Chunking**: Preserves section titles (`## Docker Compose`) alongside content to eliminate standalone header noise.
- **Fast Local Inference**: Integrates `nomic-embed-text` (vector embeddings) and `codellama:latest` (7B parameter instruct model) via Ollama.
- **Modern React Chat UI**: Interactive UI featuring source attribution cards, section badges, similarity scores, clear chat option, and example prompts.
- **Production Containerization**: Multi-stage Docker builds and Docker Compose orchestration with host networking support.
- **Automated CI/CD**: GitHub Actions pipeline for pytest verification, frontend linting, build checks, and Docker container validation.

---

## 🏗️ Architecture & RAG Pipeline Flow

```
[ User Query ]
      │
      ▼
┌───────────────────────────┐
│ 1. Vector Embedding       │ (nomic-embed-text via Ollama)
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ 2. Cosine Similarity      │ (Compare against data/embeddings.json)
└─────────────┬─────────────┘
              │
      ┌───────┴───────┐
      │ Score >= 0.60? │
      └───────┬───────┘
     YES      │      NO
      ┌───────┴───────┐
      │               │
      ▼               ▼
┌─────────────┐ ┌──────────────────────────────────────────────┐
│ Top-k Chunks│ │ Direct Fallback Response:                     │
│ Context     │ │ "I couldn't find relevant information in..." │
└──────┬──────┘ └──────────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────┐
│ 3. Grounded Prompt        │ (Strict context-only system prompt)
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ 4. Local Code Llama       │ (codellama:latest via Ollama)
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ 5. Clean API Response     │ (Answer + Section Sources + Similarity)
└───────────────────────────┘
```

---

## 📊 RAG Accuracy Evaluation Benchmark

Evaluation test suite executed across 10 benchmark questions (7 in-domain, 3 out-of-domain):

| Question | Category | Top Source | Similarity | Result | Status |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **What is Docker?** | In-domain Direct | `docker.md (What is Docker?)` | 0.8971 | Grounded Answer | **PASS** |
| **What is Docker Compose?** | In-domain Direct | `docker.md (Docker Compose)` | 0.8599 | Grounded Answer | **PASS** |
| **What is a Docker image?** | In-domain Direct | `docker.md (Docker Image)` | 0.8656 | Grounded Answer | **PASS** |
| **What is a Dockerfile?** | In-domain Direct | `docker.md (Dockerfile)` | 0.8424 | Grounded Answer | **PASS** |
| **What are common Docker commands?** | In-domain Section | `docker.md (Build an image)` | 0.7902 | Grounded Answer | **PASS** |
| **How do I list running containers in Docker?** | In-domain Paraphrased | `docker.md (List running containers)` | 0.8260 | Grounded Answer | **PASS** |
| **How do I stop a container in Docker?** | In-domain Paraphrased | `docker.md (Stop a container)` | 0.9193 | Grounded Answer | **PASS** |
| **What is quantum computing?** | Out-of-domain Invalid | *None* | 0.0000 | Rejection Fallback | **PASS** |
| **How does photosynthesis work?** | Out-of-domain Invalid | *None* | 0.0000 | Rejection Fallback | **PASS** |
| **Who is the president of the United States?** | Out-of-domain Invalid | *None* | 0.0000 | Rejection Fallback | **PASS** |

**Benchmark Results Summary**:
- **Retrieval Accuracy**: 100.0%
- **Answer Accuracy**: 100.0%
- **Out-of-Domain Rejection**: 100.0%
- **Hallucination Rate**: 0.0%

---

## 🛠️ Technology Stack

- **Frontend**: React 19, Vite, Vanilla CSS.
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic, HTTPX.
- **RAG & Embeddings**: Nomic Embed Text (`nomic-embed-text`) via Ollama.
- **LLM Engine**: Code Llama (`codellama:latest`) via Ollama.
- **Containerization**: Docker, Nginx (Alpine), Docker Compose.
- **Testing**: Pytest, FastAPI TestClient, Oxlint.
- **CI/CD**: GitHub Actions.

---

## 📁 Directory Structure

```
DevAssist-AI/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD pipeline
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint & endpoints
│   │   └── services/
│   │       ├── chunker.py      # Section-aware markdown chunker
│   │       ├── document_loader.py
│   │       ├── embedder.py     # Nomic-embed vector generator
│   │       ├── indexer.py      # Index builder with section metadata
│   │       ├── llm.py          # Code Llama inference client
│   │       ├── rag.py          # Prompt builder & out-of-domain handler
│   │       └── retriever.py    # Similarity calculator & threshold filter
│   ├── tests/
│   │   ├── eval_week2.py       # 10-question evaluation benchmark
│   │   ├── test_api.py         # API integration unit tests
│   │   ├── test_rag.py         # RAG prompt unit tests
│   │   └── test_retriever.py   # Retriever & similarity unit tests
│   ├── Dockerfile              # Backend production container configuration
│   └── requirements.txt        # Frozen Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # React chat UI & source cards
│   │   ├── App.css             # Component styling
│   │   ├── index.css           # Global layout & design tokens
│   │   └── main.jsx
│   ├── Dockerfile              # Multi-stage Vite + Nginx container
│   ├── nginx.conf              # Nginx server configuration
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── documents.json          # Indexed chunks with section metadata
│   └── embeddings.json         # Pre-computed vector embeddings
├── docs/
│   └── docker.md               # Technical knowledge source
├── compose.yaml                # Multi-container Compose orchestration
├── docker-compose.yml          # Compose alias
├── README.md
└── .gitignore
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites (Ollama Setup)
Install [Ollama](https://ollama.com/) on Windows and pull the required models:

```powershell
ollama pull nomic-embed-text
ollama pull codellama:latest
```

Verify installed models:
```powershell
ollama list
```

---

### 2. Running Locally (Development Mode)

#### Backend Setup
```powershell
cd backend
pip install -r requirements.txt

# Run indexer & embedder (optional if data/ exists)
python -m backend.app.services.indexer
python -m backend.app.services.embedder

# Start FastAPI server
python -m uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be available at `http://127.0.0.1:8000`.

#### Frontend Setup
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
Frontend UI will be available at `http://localhost:5173`.

---

### 3. Running with Docker Compose (Recommended)

Run the entire application stack using Docker Compose:

```powershell
docker compose up --build -d
```

Verify containers are running:
```powershell
docker ps
```

- **Frontend Application**: `http://localhost` (Port 80)
- **Backend API**: `http://localhost:8000` (Port 8000)
- **Health Check**: `http://localhost:8000/health`

To stop containers:
```powershell
docker compose down
```

---

## 🧪 Testing & Evaluation

### Run Backend Pytest Suite
```powershell
python -m pytest backend/tests -v
```

### Run RAG Accuracy Evaluation Benchmark
```powershell
python backend/tests/eval_week2.py
```

### Run Frontend Build & Lint Checks
```powershell
cd frontend
npm run lint
npm run build
```

---

## 🔌 API Endpoints Reference

### `GET /health`
Returns backend health status.

### `POST /ask`
Submit a question to DevAssist AI.

**Request Body**:
```json
{
  "question": "What is Docker Compose?",
  "top_k": 2,
  "similarity_threshold": 0.60
}
```

**Response**:
```json
{
  "question": "What is Docker Compose?",
  "answer": "Docker Compose is a tool used to define and run multi-container applications...",
  "sources": [
    {
      "filename": "docker.md",
      "section": "Docker Compose",
      "chunk_id": 5,
      "similarity": 0.8599
    }
  ]
}
```

---

## 🎬 Project Demonstration Script

Follow this script during a live demo:

1. **Start Stack**: Run `docker compose up -d` and open `http://localhost` in the browser.
2. **In-Domain Direct Demo**: Click **"What is Docker?"**. Show the grounded response and source card displaying `docker.md` (Section: What is Docker?, Similarity: 0.8971).
3. **In-Domain Command Demo**: Click **"What is Docker Compose?"**. Show section attribution and detailed technical answer.
4. **Out-of-Domain Rejection Demo**: Click **"What is quantum computing? (Out-of-domain test)"**.
   - Show how similarity score falls below threshold (`< 0.60`).
   - Highlight the refusal response: *"I couldn't find relevant information in the indexed documentation."*
   - Emphasize **0% hallucination rate**.
5. **Run Pytest Suite**: Execute `python -m pytest backend/tests -v` in terminal to prove 100% test pass rate.
