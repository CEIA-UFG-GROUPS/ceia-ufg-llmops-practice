# 🧪 Prática Final de LLMOps — "Pergunte ao Semestre"

Prática de encerramento do **Grupo de Estudos em MLOps — CEIA/UFG (2026)**.

Em **1 hora**, você vai juntar o que vimos no ano — **Git, GitHub, Bash, Docker, embeddings, banco vetorial e LLM** — e subir uma **API local com RAG** que responde perguntas sobre as próprias aulas do grupo.

```text
 você ──curl──▶ API (FastAPI) ──embedding local (CPU)──▶ Qdrant (Docker)
                    │                                        │
                    │◀──────────── trechos mais parecidos ───┘
                    │
                    └── pergunta + trechos ──▶ LLM (chave OpenAI) ──▶ resposta + fontes
```

| Peça | Ferramenta | Aula |
|---|---|---|
| Versionamento e entrega | Git + GitHub (fork, branch, PR) | 03 |
| Baixar o corpus | Bash | 02 |
| Embeddings locais | `fastembed` (modelo multilíngue, roda em CPU) | 06 |
| Banco vetorial | Qdrant | 07 |
| API | FastAPI | 09 |
| LLM | API compatível com OpenAI | 21 |
| Empacotamento | Docker + Docker Compose | 04 |

---

## ⏰ Pré-aula (obrigatório, ~15 min em casa)

A aula tem só 1 hora: **faça isto antes**, para não depender da rede da sala.

1. Instale **Git** e **Docker** (Docker Desktop no Windows/Mac). Teste: `docker run hello-world`.
2. Faça um **fork** deste repositório (botão *Fork* no GitHub) e clone o **seu** fork:
   ```bash
   git clone git@github.com:<seu-usuario>/ceia-ufg-llmops-practice.git
   cd ceia-ufg-llmops-practice
   ```
3. Construa as imagens (baixa o modelo de embeddings, ~500 MB):
   ```bash
   cp .env.example .env
   docker compose build
   docker compose pull qdrant
   ```

✅ Pronto quando `docker compose build` terminar sem erro.

> 💻 **Windows:** use o terminal do **WSL** ou o **Git Bash** para rodar os comandos e scripts.

---

## 📂 Estrutura

```text
.
├── app/
│   ├── main.py          # API (completa — não precisa mexer)
│   └── rag.py           # ⭐ SEU TRABALHO: TODO 1, 2 e 3
├── scripts/
│   └── get_corpus.sh    # baixa as aulas do grupo para data/
├── tests/test_rag.py    # teste do chunking
├── Dockerfile
├── docker-compose.yml   # qdrant + api
├── .env.example         # modelo das variáveis (a chave vai no .env, que NÃO é versionado)
└── requirements.txt
```

---

## 🚀 Passo a passo

### Passo 0 — Git (5 min)

```bash
git switch -c feat/rag          # nunca trabalhe direto na main
```

Abra o `.env` e cole a chave que o monitor vai te passar em `OPENAI_API_KEY=`.

> ⚠️ **A chave é um segredo.** O `.env` está no `.gitignore`. Confira com `git status`: ele **não** pode aparecer. Chave commitada = chave vazada (bots varrem o GitHub em minutos).

### Passo 1 — Bash: o corpus (5 min)

```bash
./scripts/get_corpus.sh
ls data/ | head
wc -w data/*.md | tail -1       # quantas palavras temos?
head -20 data/aula07.md
```

Leia o script: `git clone --depth 1`, `find`, `trap` e `mktemp`. Tudo isso é Bash de verdade, usado em produção.

### Passo 2 — Docker: subindo o Qdrant e a API (5 min)

```bash
docker compose up -d
docker compose ps
curl localhost:8000/health        # {"qdrant":true,"vetores":0}
```

Abra o painel do Qdrant: 👉 <http://localhost:6333/dashboard>. Ele ainda está vazio.

### Passo 3 — TODO 1 e 2: embeddings + banco vetorial (12 min)

Abra `app/rag.py`. Os comentários de cada TODO dizem exatamente o que fazer.

- **TODO 1 — `ingest()`**: crie a coleção, gere os embeddings e faça o *upsert* no Qdrant.
- **TODO 2 — `search()`**: transforme a pergunta em vetor e busque os `k` trechos mais próximos.

Depois de editar, reconstrua a API e rode a ingestão:

```bash
docker compose up -d --build api
curl -X POST localhost:8000/ingest          # {"chunks": ~690}
curl localhost:8000/health                  # vetores > 0
```

✅ **Checkpoint:** no painel do Qdrant, abra a coleção `aulas` e veja os pontos, com o vetor de 384 números e o payload (`texto`, `fonte`).

### Passo 4 — TODO 3: o LLM (12 min)

- **TODO 3 — `ask()`**: monte o contexto com os trechos, chame o LLM e devolva a resposta com as fontes.

```bash
docker compose up -d --build api
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
     -d '{"question": "o que é canary deployment?"}'
```

✅ **Checkpoint:** a resposta cita `aula22` em `fontes`. Também dá para testar pelo navegador: <http://localhost:8000/docs>.

Teste uma pergunta fora do tema ("qual a capital da França?"). O modelo deveria dizer que não sabe. Por quê?

### Passo 5 — Entrega (9 min)

```bash
git status                       # o .env NÃO pode aparecer aqui
git add app/rag.py
git commit -m "feat: implementa RAG (ingest, search, ask)"
git push -u origin feat/rag
```

No GitHub, abra um **Pull Request** do seu `feat/rag` para a `main` **do seu fork**. Na descrição, cole a resposta de uma pergunta que você fez.

---

## 🆘 Deu ruim?

| Sintoma | O que fazer |
|---|---|
| `port is already allocated` | Algo já usa a porta 6333/8000: `docker ps` e pare o container antigo |
| `permission denied` no Docker (Linux) | `sudo usermod -aG docker $USER` e abra um novo terminal |
| `{"erro": "TODO X: implemente aqui"}` | É esperado! Falta implementar aquele TODO |
| `/ask` com erro 401 | Chave errada ou faltando no `.env` → depois `docker compose up -d api` |
| `/ask` com erro 429 | Limite de uso da chave: espere alguns segundos ou peça a outra chave |
| Mudei o código e nada mudou | Faltou `docker compose up -d --build api` |
| `Collection aulas not found` | Rode o `/ingest` antes do `/ask` |

Os erros detalhados aparecem em `docker compose logs api`.

---

## ⭐ Bônus (em casa)

1. **LLM 100% local:** instale o [Ollama](https://ollama.com), rode `ollama pull qwen2.5:1.5b` e no `.env` use `OPENAI_BASE_URL=http://host.docker.internal:11434/v1` e `LLM_MODEL=qwen2.5:1.5b`. **Não precisa mudar o código.** Por quê? (No Linux, suba o Ollama com `OLLAMA_HOST=0.0.0.0 ollama serve` para o container enxergá-lo.)
2. **CI (Aula 10):** crie `.github/workflows/test.yml` que roda `pytest` a cada push.
3. **Guardrail (Aula 25):** se o melhor `score` da busca for baixo, responda "não sei" **sem** chamar o LLM. Teste com "qual a capital da França?" e "receita de bolo de cenoura": que limite separa bem as perguntas? Ele é perfeito?
4. **Experimente:** mude o `size` do `chunk()` e o `k` do `search()`. A resposta melhora ou piora?
