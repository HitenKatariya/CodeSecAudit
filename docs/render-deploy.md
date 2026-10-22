# Deploying to Render (images under ~200 MB)

This stack was reworked so each deployable image stays in the low hundreds of
megabytes instead of multi-gigabyte ML images. The main changes:

| Service | Before | After (estimated) | Why |
| --- | --- | --- | --- |
| `rag-server` | ~7.35 GB `docker images` (torch + CUDA + triton) | ~140-170 MB | Removed `sentence-transformers`/torch; embeddings now come from an external OpenAI-compatible API |
| `main-server` | ~250 MB | ~90-120 MB | Alpine multi-stage build; unused `pyjwt`/`cryptography` and other extras removed; no compilers/pip in the final layer |
| `main-worker` | ~250 MB | reuses `main-server` image | No duplicate image |
| `client` | ~592 MB | ~140-180 MB | Next.js `output: "standalone"`; final stage is plain Alpine plus only the Node binary (no npm/corepack) |

Verify locally after building:

```bash
docker build -t codesec-main ./main-server
docker build -t codesec-rag ./rag-server
docker build -t codesec-client ./client
docker images | grep codesec
```

Render's dashboard shows the pushed image size; the numbers above are
uncompressed `docker images` sizes, so the registry view is usually smaller.

## Architecture on Render

```
Browser
  └── codesec-client (Next.js web service)
        └── /api/*  ──runtime proxy──> codesec-main (FastAPI web service)
                                          ├── Render Postgres
                                          ├── Render Key Value (Redis)
                                          └── codesec-rag (FastAPI web service)
                                                ├── Qdrant Cloud
                                                └── external embedding API
GitHub ── webhooks ──> codesec-main
```

The review worker runs inline in `codesec-main` (`RUN_WORKER_INLINE=true`)
because Render's free plan does not offer background workers. On a paid plan,
set `RUN_WORKER_INLINE=false` and add a worker service running
`python -m app.jobs.worker` with the same image and environment.

## External services you must provide

### 1. Embedding provider (required for RAG)

The image no longer contains a local embedding model. Point it at any
OpenAI-compatible `POST {base}/embeddings` endpoint:

- OpenAI: `https://api.openai.com/v1`, model `text-embedding-3-small`, dim `1536`
- Jina, Voyage, Together, Groq, etc. (use their OpenAI-compatible base URL)
- Ollama / LM Studio: `http://host:11434/v1`, model e.g. `nomic-embed-text`

Environment variables:

| Variable | Example |
| --- | --- |
| `EMBEDDING_API_BASE` | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | `sk-...` (leave empty for local providers) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `EMBEDDING_DIM` | `1536` (only a default; the real dimension is detected from the API response) |
| `EMBEDDING_BATCH_SIZE` | `64` |

If these are not configured, the RAG endpoints return `503` and the main
review pipeline still works, but no guidance snippets are attached to findings.

### 2. Qdrant

Render does not offer Qdrant. Use [Qdrant Cloud](https://cloud.qdrant.io/)
(free tier is enough to start), then set:

| Variable | Example |
| --- | --- |
| `QDRANT_URL` | `https://xxxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | the cluster API key |
| `RAG_COLLECTION_NAME` | `secure_guidance_v1` |

Changing the embedding model changes the vector dimension. Use a new
`RAG_COLLECTION_NAME` (for example `secure_guidance_v2`) and re-index; the
service refuses to write into a collection with a different dimension.

## Deploy steps

1. Push this repo to GitHub.
2. In Render, choose **New → Blueprint** and select the repo. `render.yaml`
   creates `codesec-main`, `codesec-rag`, `codesec-client`, Postgres, and Key
   Value.
3. Fill in every `sync: false` variable in the dashboard:
   - `RAG_SERVICE_TOKEN` (same value on main and rag)
   - `NEXT_PUBLIC_APP_URL` = `https://<client>.onrender.com`
   - `OAUTH_REDIRECT_URI` = `https://<client>.onrender.com/api/auth/github/callback`
   - `QDRANT_URL`, `QDRANT_API_KEY`
   - `EMBEDDING_API_KEY`
   - `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_APP_ID`,
     `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`
4. In GitHub → Settings → Developer settings → OAuth Apps, set the callback URL
   to the **client** URL:
   `https://<client>.onrender.com/api/auth/github/callback`
5. Wait for the first deploy. `codesec-main` runs `alembic upgrade head` as
   part of its start command (free plans do not support `preDeployCommand`).
6. Index the corpus (see below).

## Indexing the corpus

The HTTP `POST /v1/index` endpoint is convenient for a small smoke test but can
exceed Render's request timeout for the full corpus. Run the script instead
from the Render shell/job:

```bash
python scripts/index_corpus.py
# or a subset:
python scripts/index_corpus.py --max-documents 500
```

If your Render plan does not expose a shell, run the same script from your
machine against Qdrant Cloud:

```bash
cd rag-server
python -m pip install -e .
export QDRANT_URL="https://xxxx.cloud.qdrant.io:6333"
export QDRANT_API_KEY="..."
export RAG_COLLECTION_NAME="secure_guidance_v1"
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."
export EMBEDDING_MODEL="text-embedding-3-small"
python scripts/index_corpus.py
```

Check status:

```bash
curl -H "X-Internal-RAG-Token: $RAG_SERVICE_TOKEN" \
  https://<rag>.onrender.com/v1/index/status
```

## Environment variable reference

### `codesec-main`

| Variable | Notes |
| --- | --- |
| `APP_ENV` | `production` (enables `Secure` session cookies) |
| `DATABASE_URL` | Injected from Render Postgres. `postgres://` is normalized to `postgresql+asyncpg://` |
| `REDIS_URL` | Injected from Render Key Value |
| `SESSION_SECRET` | Generated by the blueprint |
| `RAG_SERVICE_URL` | Internal host:port; the app adds `http://` if missing |
| `RAG_SERVICE_TOKEN` | Shared secret with `codesec-rag` |
| `NEXT_PUBLIC_APP_URL` | Public client URL (CORS + post-login redirect) |
| `OAUTH_REDIRECT_URI` | Public client callback URL (see above) |
| `RUN_WORKER_INLINE` | `true` on free plan |
| `GITHUB_*` | OAuth/App credentials |

### `codesec-rag`

| Variable | Notes |
| --- | --- |
| `QDRANT_URL`, `QDRANT_API_KEY` | Qdrant Cloud |
| `RAG_SERVICE_TOKEN` | Must match `codesec-main` |
| `RAG_COLLECTION_NAME` | Use a new name when changing embedding models |
| `EMBEDDING_*` | External embedding provider |

### `codesec-client`

| Variable | Notes |
| --- | --- |
| `MAIN_SERVER_URL` | Internal host:port of `codesec-main`; the runtime proxy adds `http://` |

`PORT` is injected by Render and honored by all three Dockerfiles. Locally it
defaults to `8000`, `8010`, and `3000`.

## Important caveats

- **Free web services spin down** after inactivity; the first request after a
  sleep is slow. The inline worker only runs while the service is awake.
- **Render free Postgres may expire** depending on the current plan terms. Use a
  paid database for anything long-lived.
- **No private services on free plans.** `codesec-rag` is a public web service
  protected by `RAG_SERVICE_TOKEN`. Use a private service on a paid plan if you
  do not want it publicly reachable.
- **Migrations run at startup.** Render's `preDeployCommand` is paid-plan only,
  so `render.yaml` sets a `dockerCommand` that runs `alembic upgrade head` and
  then starts Uvicorn. Alembic is idempotent, so restarts and spin-ups are safe.
- **Key Value is a service, not a database.** In `render.yaml` the Redis
  instance is declared under `services` with `type: keyvalue` and
  `ipAllowList: []` (private network only).
- **`npm ci` is not usable** because `client/package-lock.json` is absent. The
  Dockerfile uses `npm install`. Commit a lockfile and switch to `npm ci` for
  reproducible client builds.
- **Alpine wheels**: the Python images use `python:3.11-alpine` with
  `PIP_ONLY_BINARY=:all:`. All pinned dependencies have musllinux wheels. If a
  future dependency lacks one, the build fails loudly instead of silently
  compiling a huge image; switch that service to `python:3.11-slim` as a
  fallback.
- **Split-origin cookies**: the OAuth callback must go through the client proxy
  (`OAUTH_REDIRECT_URI`) or the session cookie lands on the main-server domain
  and the browser never sends it to the client.
- **Only one main-server instance** should run the inline worker. If you scale
  to multiple instances, move the worker to a dedicated service.

## Local Docker Compose

`docker-compose.yml` still runs the full stack, but the Python images no longer
contain `curl`; healthchecks use Python's `urllib`. The worker is a separate
container locally and reuses the `codesec-main-server:local` image, so only one
Python image is built.

Set `EMBEDDING_API_KEY` (and optionally `EMBEDDING_API_BASE` /
`EMBEDDING_MODEL`) in the environment or a `.env` file before bringing the
stack up if you want RAG search to return results.
