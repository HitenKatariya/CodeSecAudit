# RAG Service — OWASP Retrieval Microservice

Standalone FastAPI service. Downloads HF corpus, embeds in-memory, serves semantic search.
No imports from `backend/` or `website/` — HTTP only.

## Layout

```
rag-service/
  rag_service/main.py     # GET /, /health, POST /rag/search
  rag_service/index.py    # RagIndex: HF download + MiniLM + numpy cosine
  rag_service/schemas.py  # SearchRequest/Response
  Dockerfile | requirements.txt (env: root /.env.example, RAG_* vars)
```

## Run

```bash
cd rag-service
pip install -r requirements.txt
uvicorn rag_service.main:app --port 7860
```

Contract: `POST /rag/search {"query": "...", "top_k": 3}` → `{results[{rank,score,title,section_title,cwe_id,content,source_file}], metadata}`.
Auth: set `RAG_API_KEY`, clients send `X-CodeSec-RAG-Key`.

## Deploy to Hugging Face Space (Docker SDK)

1. Create a Space at https://huggingface.co/new-space → **Docker** SDK, port `7860`.
2. Push the contents of `rag-service/` (`rag_service/` package + `Dockerfile` + `requirements.txt`).
   The image self-contains everything (`RAG_BUILD_ON_START=true` downloads the
   corpus and builds the index at boot — no `data/` or `start.sh` needed).
3. Space Secrets: `RAG_API_KEY` (**set in production**, else the endpoint is public),
   optional `RAG_DATASET_REPO`, `RAG_EMBEDDING_MODEL`.
4. Health: `GET /health` should show `index_loaded: true`. Search:
   `POST /rag/search` with `X-CodeSec-RAG-Key` header.
