# Backend — CodeSecAudit Review API

FastAPI service. Rule-engine (`review_engine/`) + SQLite (`review_store/`) + optional RAG.

## Layout

```
backend/
  api/main.py          # routes: /, /health, /review, /review/code, /reviews, /stats, /webhook/github
  review_engine/       # critic.py, pipeline.py, retriever.py (local Chroma), remote_rag.py, github_app.py, ...
  review_store/        # db.py, repository.py, models.py (SQLite reviews.db)
  config/settings.py   # typed env (reference; api/ reads os.getenv directly)
  Dockerfile | requirements.txt (env: root /.env.example, CODESEC_* vars)
```

## Run

```bash
cd backend
pip install -r requirements.txt
# local RAG off by default; remote RAG via rag-service:
set CODESEC_RAG_MODE=remote
set CODESEC_RAG_SERVICE_URL=http://localhost:7860
uvicorn api.main:app --port 8003
```

Env: root `/.env.example` (`CODESEC_*`, `GITHUB_APP_*`). DB defaults to `data/app/reviews.db` (`CODESEC_DB_PATH`).

## Scripts (`backend/scripts/`)

Run from repo root (needs `review_engine` importable: `pip install -e .` once, or `PYTHONPATH=backend`):

| Script | Purpose |
|---|---|
| `review_code.py` | CLI: review a code snippet/file |
| `github_pr_review.py` | CLI: review a GitHub PR |
| `evaluate_reviewer.py` | Regression check vs `backend/eval/golden_cases.jsonl` |
| `smoke_test_demo_files.py`, `test_suppression.py` | Engine smoke/suppression tests |
| `check_lightweight_mode.py`, `check_main_api_remote_rag.py`, `test_remote_rag_client.py` | RAG mode checks |
| `build_rag_index.py`, `convert_owasp_cheatsheets_to_rag.py` | Local Chroma corpus/index builders (`data/`) |
| `download.py`, `normalize_*.py`, `merge_review_datasets.py`, `inspect_*.py`, `check_raw_sources.py`, `fix_owasp_python_names.py` | One-off dataset pipeline (`data/`) |
| `test_hf_dataset_load.py`, `upload_to_huggingface.py`, `upload_to_kaggle.py`, `create_release_package.py` | Dataset publish/release |
| `test_rag_service.py`, `check_remote_rag_service.py` | rag-service health checks |
| `deploy_hf_rag_space.py`, `prepare_hf_rag_space.py`, `create_deploy_pr.sh` | HF Space packaging/deploy |
| `create_github_app_manifest.py`, `complete_github_app_manifest.py`, `apply_github_app_env.py`, `verify_github_app_env.py` | GitHub App setup (writes root `.env`) |
| `docker_smoke_test.sh` | API smoke test vs running backend |

## Eval (`backend/eval/`)

`golden_cases.jsonl` — tiny regression set (clean code → APPROVE, eval/SQLi/shell/MD5 → WARNING with expected CWE). Used only by `evaluate_reviewer.py`; not loaded at runtime, not shipped in images. Keep it — it's the fastest way to verify engine changes. Run: `python backend/scripts/evaluate_reviewer.py`.
