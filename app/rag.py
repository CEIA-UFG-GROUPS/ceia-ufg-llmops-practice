"""O coração do RAG: chunking -> embeddings -> Qdrant -> LLM.

Fluxo:
  ingest():  data/*.md -> chunk() -> embedder -> upsert no Qdrant
  ask():     pergunta -> embedder -> search() no Qdrant -> prompt com contexto -> LLM
"""
import os
import uuid
from pathlib import Path

from fastembed import TextEmbedding
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

DATA_DIR = Path("data")
COLLECTION = "aulas"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 384 dims, roda em CPU

# Clientes criados uma vez, quando a API sobe
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
embedder = TextEmbedding(EMBED_MODEL)


def llm() -> OpenAI:
    # Criado sob demanda: a API sobe mesmo sem chave (e o /health funciona)
    return OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)


def qdrant_ok() -> bool:
    try:
        qdrant.get_collections()
        return True
    except Exception:
        return False


def count() -> int:
    if not qdrant_ok() or not qdrant.collection_exists(COLLECTION):
        return 0
    return qdrant.count(COLLECTION).count


def chunk(text: str, size: int = 800) -> list[str]:
    """Quebra o texto em pedaços de até `size` caracteres, respeitando parágrafos."""
    chunks, atual = [], ""
    for par in text.split("\n\n"):
        while len(par) > size:  # parágrafo gigante: corta na marra
            if atual:
                chunks.append(atual)
                atual = ""
            chunks.append(par[:size])
            par = par[size:]
        if atual and len(atual) + 2 + len(par) > size:
            chunks.append(atual)
            atual = ""
        atual = f"{atual}\n\n{par}" if atual else par
    if atual.strip():
        chunks.append(atual)
    return chunks


def ingest() -> int:
    """Lê data/*.md, gera embeddings e grava no Qdrant. Retorna o nº de chunks."""
    textos, fontes = [], []
    for arquivo in sorted(DATA_DIR.glob("*.md")):
        for c in chunk(arquivo.read_text(encoding="utf-8")):
            textos.append(c)
            fontes.append(arquivo.stem)
    if not textos:
        raise RuntimeError("data/ está vazio: rode ./scripts/get_corpus.sh antes")

    # TODO 1 (Aulas 06 e 07) ------------------------------------------------
    # a) Crie a coleção (se ainda não existir) com vetores de 384 dimensões e distância cosseno
    # b) Gere os vetores: embedder.embed(textos) devolve um gerador de arrays numpy
    # c) Faça upsert de um PointStruct por chunk, com payload {"texto": ..., "fonte": ...}
    #    Dica: id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{fonte}-{i}")) deixa o ingest idempotente
    if not qdrant.collection_exists(COLLECTION):
        qdrant.create_collection(
            COLLECTION, vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
    vetores = embedder.embed(textos)
    pontos = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{fonte}-{i}")),
            vector=vetor.tolist(),
            payload={"texto": texto, "fonte": fonte},
        )
        for i, (texto, fonte, vetor) in enumerate(zip(textos, fontes, vetores))
    ]
    qdrant.upsert(COLLECTION, points=pontos)
    # -----------------------------------------------------------------------
    return len(textos)


def search(pergunta: str, k: int = 4) -> list[dict]:
    """Busca semântica: devolve os k chunks mais parecidos com a pergunta."""
    # TODO 2 (Aula 07) --------------------------------------------------------
    # a) Gere o vetor da pergunta (mesmo embedder do ingest!)
    # b) qdrant.query_points(COLLECTION, query=vetor, limit=k).points
    # c) Devolva [{"texto": ..., "fonte": ..., "score": ...}, ...]
    vetor = next(embedder.embed([pergunta])).tolist()
    pontos = qdrant.query_points(COLLECTION, query=vetor, limit=k).points
    return [{**p.payload, "score": round(p.score, 3)} for p in pontos]
    # -----------------------------------------------------------------------


PROMPT = """Você é um monitor do Grupo de Estudos em MLOps do CEIA/UFG.
Responda à pergunta usando APENAS o contexto abaixo, em português, de forma curta.
Se o contexto não tiver a resposta, diga que não sabe.

Contexto:
{contexto}

Pergunta: {pergunta}"""


def ask(pergunta: str) -> dict:
    """RAG completo: busca o contexto e pede a resposta ao LLM."""
    trechos = search(pergunta)

    # TODO 3 (Aula 21) --------------------------------------------------------
    # a) Monte o contexto juntando os trechos (ex.: "[aula22] texto...")
    # b) Chame llm().chat.completions.create(model=os.getenv("LLM_MODEL"), messages=[...],
    #    max_tokens=400) com o PROMPT preenchido
    # c) Devolva {"resposta": ..., "fontes": [lista de aulas sem repetição]}
    contexto = "\n\n".join(f"[{t['fonte']}] {t['texto']}" for t in trechos)
    r = llm().chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": PROMPT.format(contexto=contexto, pergunta=pergunta)}],
        max_tokens=400,
    )
    return {
        "resposta": r.choices[0].message.content,
        "fontes": sorted({t["fonte"] for t in trechos}),
    }
    # -----------------------------------------------------------------------
