from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.services.rag import build_prompt
from backend.app.services.llm import generate_answer

app = FastAPI(title="DevAssist AI")


# Allow the React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "DevAssist AI is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ask")
def ask(question: str):

    # Step 1: Retrieve relevant documentation
    prompt, sources = build_prompt(
        question,
        top_k=2
    )

    # Step 2: Send the RAG prompt to Code Llama
    answer = generate_answer(prompt)

    # Step 3: Return answer and sources
    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "filename": source["filename"],
                "chunk_id": source["id"],
                "similarity": round(source["score"], 4),
            }
            for source in sources
        ],
    }
