FROM python:3.12-slim
WORKDIR /code
ENV FASTEMBED_CACHE_PATH=/models
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Baixa o embedder no build (pre-aula), assim a aula nao depende da rede
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
COPY app ./app
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
