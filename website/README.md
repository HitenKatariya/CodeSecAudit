# Website — CodeSecAudit Flask Frontend

Flask SaaS site: landing, GitHub OAuth, email OTP, dashboard, usage. Talks to
`backend/` only via HTTP (`api_client.fetch_reviews(CODESEC_API_URL)`); degrades to
empty state when backend is unreachable. Own MongoDB/MemDB + Resend email.

## Run

```bash
cd website
pip install -r requirements.txt
# from repo root:
gunicorn website.app:app --bind 0.0.0.0:5000
# or dev:
set CODESEC_API_URL=http://localhost:8003
python -m flask --app website.app run -p 5000
```

Env: root `/.env.example`. Render deploys via `website/Dockerfile` (replaces old
`deploy/render/website.Dockerfile`). Docker image rebuilds `website/` package at
`/app/website` so `website.*` imports work unchanged.
