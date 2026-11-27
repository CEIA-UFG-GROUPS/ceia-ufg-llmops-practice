# 🧑‍🏫 Guia do Monitor — Prática Final de LLMOps

> Esta é a branch **`solucao`**. Ela tem o `app/rag.py` resolvido e este roteiro.
> O gabarito exato do que os alunos precisam escrever é:
>
> ```bash
> git diff main solucao -- app/rag.py
> ```

---

## 📅 Antes da aula

### D-3: avisar a turma
Mande no grupo o link do repositório e peça a **Pré-aula** do README (instalar Docker, fazer fork, `docker compose build`). Sem isso, a sala inteira baixa ~500 MB ao mesmo tempo e a aula não cabe em 1h.

> Sugestão de mensagem: "Pessoal, a prática final de LLMOps é na próxima aula. Antes, façam a seção **Pré-aula** do README (15 min): <link>. Quem chegar sem o `docker compose build` feito vai perder metade da prática."

### D-1: chaves
- Peça ao Lucas as **2 chaves** e teste cada uma:
  ```bash
  curl https://api.openai.com/v1/chat/completions -H "Authorization: Bearer $KEY" \
    -H 'content-type: application/json' \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"oi"}],"max_tokens":5}'
  ```
- Divida a turma em duas metades: a **metade A** usa a chave 1 e a **metade B** usa a chave 2. Isso ajuda com o limite de requisições (429).
- **Entregue as chaves no privado ou em papel, nunca no grupo nem no repositório.** Combine com o Lucas de **revogar as chaves logo após a aula**.
- Custo estimado: cada `/ask` gasta cerca de 1,5k tokens de entrada e no máximo 400 de saída. Com um modelo barato, isso dá frações de centavo por pergunta. A turma inteira deve gastar menos de US$ 1.

### No dia, antes de começar
- Rode a prática inteira na sua máquina (seção **Teste rápido** abaixo) para ter a tela pronta para mostrar.
- Deixe o painel do Qdrant (`localhost:6333/dashboard`) aberto com a coleção `aulas` populada.

---

## ⏱️ Roteiro minuto a minuto (60 min)

| Min | Etapa | O que fazer / falar |
|---|---|---|
| 0–5 | **Abertura** | Mostre o diagrama do README. A mensagem central é que **o LLM é a peça menor**. O que faz o sistema funcionar é a operação em volta: versionamento, containers, dados, busca e segredos. Pergunte quem fez a pré-aula e mande quem não fez rodar `docker compose build` **agora**. |
| 5–10 | **Passo 0: Git** | Distribua as chaves. Peça a todos `git switch -c feat/rag`, depois `cp .env.example .env` (se ainda não fizeram), colar a chave e rodar `git status`. 🔎 **Confira:** o `.env` não pode aparecer. Explique o `.gitignore`: chave no GitHub é vazada em minutos. |
| 10–15 | **Passo 1: Bash** | Rodem `./scripts/get_corpus.sh`. Abra o script e comente `set -euo pipefail` (falhar cedo), `trap ... EXIT` (limpeza garantida) e `find` + `basename`/`dirname`. ✅ Esperado: `Corpus pronto: 25 aulas em data/`. |
| 15–20 | **Passo 2: Docker** | Rodem `docker compose up -d` e `curl localhost:8000/health`. ✅ Esperado: `{"qdrant":true,"vetores":0}`. Mostre o `docker-compose.yml`: são 2 serviços, a API acha o Qdrant pelo **nome do serviço** (`http://qdrant:6333`, Aula 04, networks) e há um volume para persistir os vetores. |
| 20–32 | **Passo 3: TODO 1 e 2** | Deixe codarem. Passe nas mesas. Aos ~27 min, quem estiver travado pode olhar a dica abaixo. ✅ Esperado: o `/ingest` retorna cerca de **692 chunks** e leva uns 20 s em CPU. Mostre o painel do Qdrant: o ponto, o vetor com 384 números e o payload. Explique que o mesmo embedder precisa ser usado no ingest e na busca. |
| 32–44 | **Passo 4: TODO 3** | ✅ Esperado: "o que é canary deployment?" retorna `fontes` com `aula22`. Peça para testarem "qual a capital da França?" e discutam por que o prompt manda dizer "não sei". |
| 44–53 | **Passo 5: Entrega** | Peça `git status` (o `.env` não pode estar lá), depois commit, push e PR **no próprio fork**. Peça para colarem uma resposta na descrição do PR. Quem terminar cedo já pode começar o bônus 3 (guardrail). |
| 53–60 | **Fechamento** | Perguntas de discussão (abaixo). Mostre o mapa "Peça → Aula" do README: cada peça foi uma aula do ano. |

### Se o tempo apertar
- **Atrasado em 10 min:** faça o TODO 3 ao vivo no projetor enquanto eles copiam.
- **Docker não funciona na máquina de alguém:** coloque a pessoa em dupla com um colega. A entrega pode ser um PR em dupla.
- **Rede caiu:** quem fez o `docker compose build` em casa continua sem problema. Só o `get_corpus.sh` e a chamada ao LLM precisam de rede.

---

## 🔑 Gabarito com dicas (para quem travar)

**TODO 1: `ingest()`**
```python
if not qdrant.collection_exists(COLLECTION):
    qdrant.create_collection(COLLECTION, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
vetores = embedder.embed(textos)
pontos = [
    PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{fonte}-{i}")),
                vector=vetor.tolist(), payload={"texto": texto, "fonte": fonte})
    for i, (texto, fonte, vetor) in enumerate(zip(textos, fontes, vetores))
]
qdrant.upsert(COLLECTION, points=pontos)
```
- **Erro comum:** passar o array numpy direto. Use `.tolist()`.
- **Por que `uuid5`?** O id é derivado de `fonte + posição`, então rodar o `/ingest` duas vezes **sobrescreve** em vez de duplicar (ingest idempotente). Com `uuid4()` aleatório, cada ingest dobraria a coleção. Vale mostrar isso.

**TODO 2: `search()`**
```python
vetor = next(embedder.embed([pergunta])).tolist()
pontos = qdrant.query_points(COLLECTION, query=vetor, limit=k).points
return [{**p.payload, "score": round(p.score, 3)} for p in pontos]
```
- **Erro comum:** esquecer que `embed()` devolve um **gerador**. É preciso usar `next(...)` (ou `list(...)[0]`) para pegar o vetor.
- **Erro comum:** usar outro modelo de embeddings na busca. A dimensão até pode bater, mas os resultados viram lixo.

**TODO 3: `ask()`**
```python
contexto = "\n\n".join(f"[{t['fonte']}] {t['texto']}" for t in trechos)
r = llm().chat.completions.create(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    messages=[{"role": "user", "content": PROMPT.format(contexto=contexto, pergunta=pergunta)}],
    max_tokens=400,
)
return {"resposta": r.choices[0].message.content, "fontes": sorted({t["fonte"] for t in trechos})}
```

---

## ✅ Respostas esperadas (validadas)

| Pergunta | `fontes` esperadas |
|---|---|
| o que é canary deployment? | `aula22` |
| para que serve o DVC? | inclui `aula16` |
| o que é um model registry? | inclui `aula19` |
| qual a capital da França? | qualquer uma, mas a resposta deve dizer que **não sabe** |

O texto da resposta varia conforme o modelo. O que importa é que as **fontes** batam.

Scores de busca medidos (cosseno): "canary deployment" ≈ **0,63**; "capital da França" ≈ **0,42**; "bolo de cenoura" ≈ **0,56**. Por isso um limite fixo de score **não** é um guardrail perfeito, o que rende uma boa discussão para o bônus 3.

---

## 🆘 Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `port is already allocated` | Container antigo ou outro serviço usando a porta | `docker ps`, depois `docker stop <id>`, ou trocar a porta no compose |
| `permission denied ... docker.sock` | Usuário fora do grupo docker (Linux) | `sudo usermod -aG docker $USER` e abrir um novo login |
| Build lento ou falhando | Pré-aula não feita, rede da sala | Colocar em dupla com quem já tem a imagem |
| `NotImplementedError: TODO X` | Esperado | Implementar o TODO |
| 401 no `/ask` | Chave errada, ou `.env` alterado sem recriar o container | Corrigir o `.env` e rodar `docker compose up -d api` (o `env_file` só é lido na criação) |
| 429 no `/ask` | Limite da chave | Esperar e trocar a metade da turma para a outra chave |
| `APIConnectionError` usando Ollama | No Linux o Ollama escuta só em 127.0.0.1 | `OLLAMA_HOST=0.0.0.0 ollama serve` |
| Mudou o código e nada mudou | A imagem não foi reconstruída | `docker compose up -d --build api` |
| `Collection aulas not found` | Chamou o `/ask` antes do `/ingest` | Rodar `curl -X POST localhost:8000/ingest` |
| **Chave commitada** | 🚨 | Avisar o Lucas para **revogar na hora**. Depois `git rm --cached .env` e commitar. Lembrar que o histórico continua com a chave, por isso revogar é obrigatório. |

---

## 💬 Perguntas para o fechamento

1. Por que o embedder roda **localmente** e o LLM não? (Custo, tamanho e latência: um embedder de 100 MB roda em CPU, um LLM bom não.)
2. Se trocarmos o modelo de embeddings, o que acontece com os vetores já gravados? (É preciso **reindexar** tudo, porque vetores de modelos diferentes não são comparáveis. É o mesmo raciocínio do model registry, Aula 19.)
3. Quanto custa cada pergunta? Como mediríamos isso em produção? (Tokens por requisição, logs e observabilidade, Aula 11.)
4. Como saber se uma mudança no `chunk size` ou no `k` **melhorou** o sistema? (Golden set e avaliação como gate de CI, Aula 25.)
5. O que falta para colocar isso em produção? (Autenticação, rate limit, CI/CD, monitoramento, deploy no Kubernetes, Aulas 10, 12 e 22.)

---

## 🧪 Teste rápido (para o monitor validar antes da aula)

```bash
git switch solucao
./scripts/get_corpus.sh
cp .env.example .env    # e preencha a chave
docker compose up -d --build
curl -X POST localhost:8000/ingest
curl -X POST localhost:8000/ask -H 'content-type: application/json' -d '{"question":"o que é canary deployment?"}'
docker compose run --rm -v "$PWD/tests:/code/tests" api python -m pytest -q tests
```
