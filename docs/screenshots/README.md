# Screenshots

This directory should contain screenshots for documentation, demos, and the README.

## Screenshot Checklist

Capture the following screenshots and save them in this directory:

| # | Screenshot | Description | Status |
|---|---|---|---|
| 1 | `github_pr_review_severe.png` | GitHub PR page showing CodeSecAudit blocking merge on critical/high risk vulnerabilities | Captured |
| 2 | `github_pr_review_healthy.png` | GitHub PR page showing CodeSecAudit approving clean diff (0.00 / 10.0 CVSS risk) | Captured |
| 3 | `github_pr_review_bugs.png` | Detected vulnerabilities with inline PR comments | Captured |
| 4 | `github_pr_review_suggest.png` | AI-powered fix suggestions in pull request review | Captured |
| 5 | `dashboard-stats.png` | Streamlit dashboard with stats cards, verdict chart, and recent reviews | Pending |
| 6 | `review-detail.png` | Review detail page showing full issue breakdown | Pending |
| 7 | `codesecrag_api_swagger.png` | FastAPI Swagger UI at `/docs` showing all endpoints | Captured |
| 8 | `kaggle-notebook.png` | Kaggle notebook preview showing dataset exploration | Pending |
| 9 | `hf-dataset.png` | Hugging Face dataset page for CodeSecAudit-RAG | Captured |
| 10 | `rag_service_swagger.png` | RAG service Swagger endpoint documentation | Captured |

## How to Capture

### GitHub Screenshots (1–3)

1. Create a test PR with `examples/vulnerable_pr_demo.py`
2. Wait for the GitHub Action to complete
3. Capture the PR comments section (screenshot 1)
4. Click on an inline comment in the Files Changed tab (screenshot 2)
5. Go to the Actions tab and open the workflow run (screenshot 3)

### Dashboard (4–5)

1. Run `docker compose up --build`
2. Submit a few reviews:
   ```bash
   curl -X POST http://localhost:8003/review/code -H "Content-Type: application/json" \
     -d '{"code": "eval(user_input)", "file_path": "demo.py"}'
   ```
3. Open http://localhost:8502 and capture the dashboard (screenshot 4)
4. Click a review to open the detail view (screenshot 5)

### API Docs (6)

1. Run `docker compose up --build`
2. Open http://localhost:8003/docs
3. Capture the Swagger UI page (screenshot 6)

### External Services (7–9)

1. Open https://www.kaggle.com/code/hitenkatariya/codesecaudit-rag and capture (screenshot 7)
2. Open https://huggingface.co/datasets/hitenvk22/CodeSecAudit-RAG-Shuffled and capture (screenshot 8)
3. Run `curl https://codesec-rag-xp4b.onrender.com/health` and capture the response (screenshot 9)
