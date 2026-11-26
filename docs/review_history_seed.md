# Seeding CodeSecAudit PR reviews into PostgreSQL

Historical PR reviews posted by the CodeSecAudit GitHub App (`@codesecaudit-ai`
and `@codesecurityaudit-app`) are backfilled into the same `reviews`,
`findings`, `review_jobs` and `audit_events` tables used by live webhooks, so
the dashboard shows one consistent dataset.

## 1. CLI seed (any environment with DB + GitHub access)

Run from `main-server/` with `DATABASE_URL` pointing at the target deployment
database:

```bash
export DATABASE_URL="<target neon postgres url>?sslmode=require"
export GITHUB_TOKEN="$(gh auth token)"

.venv/bin/python -m app.scripts.seed_github_reviews \
  --repo OMCHOKSI108/CodeSecurityAuditAgent \
  --repo HitenKatariya/CodeSecAudit
```

Use `--org-slug <slug>` to force a specific tenant organization. Without it the
script resolves the org from the repository owner via existing membership.
Re-running is idempotent: PR + commit SHA pairs already present are skipped.

## 2. Live sync (no local DB credentials needed)

Sign in on the deployed client, then either:

- open **Pull Requests** and click **Sync GitHub PRs**, or
- `POST /api/reviews/sync-github` through the client proxy.

The backend uses its own GitHub App installation token and database, applies
the idempotent Alembic migration (`005_add_org_policy_json`), and imports all
CodeSecAudit bot comments for every repository visible to the tenant.

## 3. Data consistency

Imported verdicts, CVSS scores, commit SHAs and findings are parsed directly
from the bot's `CODESEC_AGENT_PAYLOAD` JSON block (with a markdown-table
fallback), so database values match the comments on GitHub exactly. Dynamic
policy threshold changes are simulated on the Policies page and, when saved,
re-evaluate stored reviews through the Policies API.
