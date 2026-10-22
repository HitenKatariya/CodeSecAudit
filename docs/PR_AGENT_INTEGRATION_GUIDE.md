# PR-Agent Architecture & Integration Guide

This guide is designed for developers and AI agents integrating the `pr_agent/` module into another project. It breaks down the internal architecture, data flow, component responsibilities, required dependencies, and practical integration patterns.

---

## 1. Directory Breakdown

```
pr_agent/
├── agent/            # Command routing & execution policy
├── algo/             # Core algorithms: diff compression, token fitting, AI callers, output models
├── config_loader.py  # Dynaconf-based configuration loader
├── git_providers/    # Provider abstractions (GitHub, GitLab, Bitbucket, Local Git, Plain Diff)
├── identity_providers/ # User identity verification
├── log.py            # Loguru-based structured logging
├── secret_providers/ # Secret management (Environment, AWS Secrets Manager)
├── servers/          # Webhook servers (FastAPI/Uvicorn) - optional
├── settings/         # Prompt templates (.toml) & default configuration
└── tools/            # Concrete review capabilities (/review, /describe, /improve, /ask)
```

### Key Modules & Responsibilities

| Directory / Module | Role | Core Files |
| :--- | :--- | :--- |
| `pr_agent/algo/` | **The Brain & Algorithms** | • `pr_processing.py`: Token compression, diff fitting, language sorting.<br>• `git_patch_processing.py`: Hunk extraction, line number calculation.<br>• `token_handler.py` & `token_budget.py`: Token counting (`tiktoken`) & budget clipping.<br>• `output_models.py`: Pydantic models for structured review outputs.<br>• `ai_handlers/`: LiteLLM integration for multi-model LLM calls.<br>• `language_handler.py`: Programming language recognition & ignoring generated files. |
| `pr_agent/settings/` | **Prompts & Configs** | • `pr_reviewer_prompts.toml`: Strict Jinja2 prompt template for `/review`.<br>• `pr_code_suggestions_prompts.toml`: Prompts for code suggestions + self-reflection.<br>• `pr_description_prompts.toml`: Prompts for PR walkthroughs & summaries.<br>• `configuration.toml`: Global settings and defaults. |
| `pr_agent/tools/` | **Tool Orchestration** | • `pr_reviewer.py`: Coordinates diff loading, prompt rendering, LLM calls, validation, and Markdown formatting.<br>• `pr_code_suggestions.py`: Generates inline suggestions and runs self-reflection.<br>• `pr_description.py`: Summarizes PR context. |
| `pr_agent/git_providers/` | **Git Abstraction** | • `git_provider.py`: Abstract Base Class for Git operations.<br>• `local_git_provider.py`: Runs against a local Git clone.<br>• `plain_diff_provider.py`: Runs against raw text diff strings (`git diff`).<br>• `github_provider.py`, `gitlab_provider.py`, etc.: Provider API implementations. |
| `pr_agent/agent/` | **Dispatcher & Router** | • `pr_agent.py`: `PRAgent` class mapping commands (`review`, `describe`, `improve`) to classes in `pr_agent/tools/`. |
| `pr_agent/config_loader.py` | **Config Accessor** | Provides `get_settings()` via Dynaconf, merging settings from `settings/configuration.toml`, `.pr_agent.toml`, and environment variables. |

---

## 2. Review Pipeline: How It Works Internally

When a review is triggered (`/review`), the pipeline follows this exact sequence:

```
[ Git Provider / Diff Input ]
             │
             ▼
1. Fetch Raw Diff & PR Metadata
             │
             ▼
2. Git Patch Processing (git_patch_processing.py)
   ├── Parse hunks and compute absolute file line numbers
   └── Prune deletion-only hunks, expand hunk context by 3-10 lines
             │
             ▼
3. Token-Aware Diff Compression (pr_processing.py)
   ├── Exclude binary & auto-generated files
   ├── Sort files by primary repository programming languages
   ├── Fit patches into prompt budget using tiktoken
   └── Summarize overflow files under "Additional modified files"
             │
             ▼
4. Prompt Assembly & Rendering (pr_reviewer.py + Jinja2)
   ├── Inject variables: diff, language, ticket requirements, repository context
   └── Render strict Jinja2 template from `settings/pr_reviewer_prompts.toml`
             │
             ▼
5. Model Call via LiteLLM (ai_handlers/litellm_ai_handler.py)
   ├── Dispatches to configured model (GPT-4o, Claude 3.5, Gemini, Ollama, etc.)
   └── Enforces structured YAML output matching Pydantic schemas
             │
             ▼
6. Response Validation & Parsing (algo/output_models.py)
   ├── Parses YAML into `PRReview` Pydantic model
   └── Validates key issues, risk levels, failure modes, and effort estimates
             │
             ▼
7. Output Publishing / Formatting
   ├── Formats Markdown summary
   └── (Optional) Publishes inline comments to GitHub/GitLab via `InlineCommentStore`
```

---

## 3. How to Integrate into Another Project

### Step 1: Install Required Dependencies

Ensure Python `>= 3.12` is installed. Add these core dependencies to your project's `pyproject.toml` or `requirements.txt`:

```bash
pip install \
  litellm \
  pydantic \
  jinja2 \
  tiktoken \
  dynaconf \
  unidiff \
  pyyaml \
  loguru \
  starlette-context \
  GitPython \
  aiohttp \
  tenacity
```

*(Optional git provider SDKs if interacting with remote APIs: `PyGithub`, `python-gitlab`, `atlassian-python-api`, `azure-devops`)*

---

### Step 2: Configure Environment Variables

The agent requires an LLM provider key and (optionally) Git tokens:

```bash
# Model Provider Key (at least one is required). These exact env var names
# are read by pr_agent's LiteLLM handler - see
# pr_agent/algo/ai_handlers/cloud_auth.py (CORRECTED: not OPENAI_KEY).
export OPENAI_API_KEY="sk-..."
# or ANTHROPIC_API_KEY="sk-ant-..."
# or GEMINI_API_KEY="..."

# Optional: Git Platform Token (if querying GitHub/GitLab PRs)
export GITHUB_TOKEN="ghp_..."
```

---

### Step 3: Minimal Integration Example (Programmatic Python API)

Here are the two simplest ways to call the review logic directly from your application code:

#### Pattern A: Using `PRAgent` (High-Level Dispatcher)

```python
import asyncio
from pr_agent.agent.pr_agent import PRAgent

async def main():
    agent = PRAgent()
    
    # 1. Review a remote PR:
    pr_url = "https://github.com/owner/repo/pull/123"
    result = await agent.handle_request(pr_url, ["review"])
    print("Review Completed:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

#### Pattern B: Reviewing a Local Git Diff (Raw Patch String)

If your project receives diffs from a local git commit, IDE, or custom API:

```python
import asyncio
from pr_agent.config_loader import get_settings
from pr_agent.tools.pr_reviewer import PRReviewer

# Sample raw diff
SAMPLE_DIFF = """diff --git a/app.py b/app.py
index e69de29..d95f3ad 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,5 @@
 def handle_auth(token):
+    if not token:
+        raise ValueError("Token missing")
     return True
"""

async def review_diff(raw_diff_text: str):
    # There is no PlainDiffProvider class to construct directly - the real
    # class is PlainDiffGitProvider, and get_git_provider_with_context()
    # auto-selects it the moment PLAIN_DIFF.CONTENT is set (see
    # pr_agent/git_providers/__init__.py). pr_url is ignored in this mode.
    get_settings().set("PLAIN_DIFF.CONTENT", raw_diff_text)

    reviewer = PRReviewer(pr_url=None)
    await reviewer.run()  # returns None; the parsed result lands on the instance
    return reviewer._structured_review_data  # {"review": {...}, "usage": {...}}

if __name__ == "__main__":
    output = asyncio.run(review_diff(SAMPLE_DIFF))
    print(output)
```

---

### Step 4: Accessing Structured Review Data Directly

If your application needs structured JSON/Pydantic output rather than Markdown comments:

```python
from pr_agent.algo.output_models import PRReview

# The tool parses the LLM output into `PRReview` Pydantic model:
# review.key_issues_to_review -> list of discrete issues (file, start_line, end_line, issue_content)
# review.risk_level           -> 'low', 'medium', or 'high'
# review.merge_recommendation -> 'no_concerns_found', 'needs_review', or 'changes_required'
# review.failure_modes        -> concrete post-merge failure scenarios
```

---

## 4. What Can Be Customized

1. **Change the LLM Model**:
   Edit `pr_agent/settings/configuration.toml` or set via environment variable:
   ```bash
   export CONFIG_MODEL="gpt-4o"
   # or "claude-3-5-sonnet-20241022", "gemini/gemini-1.5-pro", "ollama/deepseek-coder", etc.
   ```
2. **Adjust Review Strictness & Features**:
   In `pr_agent/settings/configuration.toml` under `[pr_reviewer]`:
   * `require_score = true/false` (rate PR 0-100)
   * `require_tests = true/false` (check for test coverage)
   * `require_security_review = true/false` (explicit security check)
   * `num_max_findings = 5` (limit max issues reported)
3. **Customize Prompts**:
   Find `pr_reviewer_prompts.toml` inside the installed package
   (`python -c "import pr_agent, os; print(os.path.dirname(pr_agent.__file__))"` → `settings/pr_reviewer_prompts.toml`)
   to modify the review persona, organizational guidelines, or output formatting - or override
   specific fields at runtime instead, the way `pr_agent_client.py` does with `EXTRA_INSTRUCTIONS`.

---

## 5. Integration Status in This Repo

There used to be a local, gitignored `pr_agent/` reference clone in this repo for exploring the
upstream source while building this integration; it has since been deleted (confirmed unused -
`main-server` depends on the published `pr-agent` PyPI package instead, pinned in
`main-server/pyproject.toml`, which is what actually runs). Everything in this section was
verified against a real `pip install .` of `main-server` in a clean virtualenv, not just read
from source. It's wired into the existing review pipeline as an **additive** LLM stage next to
the deterministic regex engine - not a replacement for it.

| Concern | File |
| :--- | :--- |
| GitHub App JWT + installation token minting (was previously unused config) | `main-server/app/security/github_app.py` |
| Real PR diff fetch on webhook (previously hardcoded to `""`) | `main-server/app/api/webhooks.py` |
| Diff splitting / added-line extraction for the regex engine | `main-server/app/reviews/diff_parser.py` (`split_diff_by_file`, `extract_added_lines`) |
| Pattern-B `PRReviewer` call, mapped into the existing `Finding` shape | `main-server/app/reviews/pr_agent_client.py` |
| Merge point: regex findings + AI findings -> same risk score / verdict / tables | `main-server/app/jobs/worker.py::process_single_job` |
| Feature flag + model selection | `PR_AGENT_REVIEW_ENABLED`, `PR_AGENT_MODEL` in `.env.example` / `app/core/config.py` |
| Markdown formatting of the final result | `main-server/app/reviews/report_formatter.py::format_pr_comment` |
| Posting the result back as a PR comment (GitHub emails watchers automatically) | `main-server/app/security/github_app.py::post_pr_comment` |
| Model fallback chain (Groq -> NVIDIA NIM -> Hugging Face) | `PR_AGENT_FALLBACK_MODELS` in `.env.example` / `app/core/config.py` |

**Verified live, found 2 real bugs by actually running it (not just reading code):**
1. `pyjwt==2.13.0` conflicted with `pr-agent`'s own `PyJWT>=2.15.1,<3` requirement -
   `pip install .` would have hard-failed on every deploy. Fixed in `main-server/pyproject.toml`.
2. litellm doesn't know the context window for `nvidia_nim/*` or `huggingface/*` model ids and
   refuses to run at all without `config.custom_model_max_tokens` set (confirmed against
   `pr_agent/algo/token_budget.py`) - without it, both fallbacks fail immediately regardless of
   credentials. Fixed in `pr_agent_client.py`.

A live call through the full fallback chain (Groq -> NVIDIA NIM -> HF) confirmed each one is
reached in order and fails on its own credential error, not a code error - meaning the wiring
itself is correct; whether it actually produces findings depends on valid keys in `.env`.

**Why additive, not a replacement:** the regex engine (`app/reviews/engine.py`) is free,
deterministic, and CWE-tagged - it stays as the always-on first pass. `pr_agent` only runs
when `PR_AGENT_REVIEW_ENABLED=true` and an LLM key (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, read
directly by `pr_agent` itself) is present, and a failure in that stage is swallowed so the
deterministic verdict is never blocked by an LLM outage (`pr_agent_client.py` catches broadly
and returns `[]`).

**Known cost of this integration:** `pr-agent` pulls in `tiktoken`/`litellm`, which don't
reliably ship musllinux wheels, so `main-server/Dockerfile` moved its base image from
`python:3.11-alpine` to `python:3.11-slim` (~130MB heavier) to get manylinux wheels instead of
compiling on musl.

**Not done (out of scope for this pass):** inline PR comment publishing (findings only land in
the `findings` table via the existing API, same as the regex engine's output), incremental
review mode, and non-GitHub providers.
