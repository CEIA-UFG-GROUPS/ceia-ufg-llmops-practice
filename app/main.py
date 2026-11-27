"""API do RAG. Este arquivo esta completo: o trabalho de voces esta em app/rag.py."""
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import rag

app = FastAPI(title="Pergunte ao Semestre")


@app.exception_handler(NotImplementedError)
def todo_pendente(_, erro):
    # Mostra no curl qual TODO ainda falta, em vez de um 500 genérico
    return JSONResponse(status_code=501, content={"erro": str(erro)})


class Question(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"qdrant": rag.qdrant_ok(), "vetores": rag.count()}


@app.post("/ingest")
def ingest():
    return {"chunks": rag.ingest()}


@app.post("/ask")
def ask(q: Question):
    return rag.ask(q.question)
