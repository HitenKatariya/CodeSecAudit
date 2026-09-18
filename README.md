# CodeSecAudit-RAG

**A Retrieval-Augmented pipeline for source-code vulnerability detection and security-fix guidance**, built on a unified, CWE/OWASP-labeled vulnerability dataset and a cheat-sheet-grounded retrieval corpus.

- Dataset (HF): [`hitenvk22/CodeSecAudit-RAG-Shuffled`](https://huggingface.co/datasets/hitenvk22/CodeSecAudit-RAG-Shuffled)
- Prototype notebook (Kaggle): [`CodeSecAudit-RAG`](https://www.kaggle.com/code/hitenkatariya/codesecaudit-rag)

## Live Deployment

| # | Service | Link |
|---|---|---|
| 1 | Website (live app) | [codesecaudit.vercel.app](https://codesecaudit.vercel.app) |
| 2 | Backend API — Swagger docs | [codesecaudit-backend.onrender.com/docs](https://codesecaudit-backend.onrender.com/docs) |
| 3 | Backend API — health check | [codesecaudit-backend.onrender.com/health](https://codesecaudit-backend.onrender.com/health) |
| 4 | RAG Service — search UI/API | [codesec-rag-service.onrender.com](https://codesec-rag-service.onrender.com/) |
| 5 | RAG Service — health check | [codesec-rag-service.onrender.com/health](https://codesec-rag-service.onrender.com/health) |
| 6 | GitHub App — install page | [github.com/apps/codesecurityaudit-app](https://github.com/apps/codesecurityaudit-app) |
| 7 | Source code (GitHub) | [hitenkatariya/CodeSecAudit](https://github.com/hitenkatariya/CodeSecAudit) |
| 8 | Dataset (Hugging Face) | [hitenvk22/CodeSecAudit-RAG-Shuffled](https://huggingface.co/datasets/hitenvk22/CodeSecAudit-RAG-Shuffled) |
| 9 | Prototype notebook (Kaggle) | [CodeSecAudit-RAG](https://www.kaggle.com/code/hitenkatariya/codesecaudit-rag) |

## System Overview (as deployed)

Three independent services, wired over HTTP (CWE ID is the join key):

| Service | Folder | Role | Live |
|---|---|---|---|
| Website (Flask) | `website/` | Landing, GitHub OAuth login, email OTP, usage dashboard, review history | [codesecaudit.vercel.app](https://codesecaudit.vercel.app) |
| Backend (FastAPI) | `backend/` | Rule-engine review (`review_engine/`), SQLite history (`review_store/`), GitHub PR webhook bot | [codesecaudit-backend.onrender.com](https://codesecaudit-backend.onrender.com/) |
| RAG Service (FastAPI) | `rag-service/` | OWASP cheat-sheet semantic search over 2,833 chunks (ONNX MiniLM, no torch) | [codesec-rag-service.onrender.com](https://codesec-rag-service.onrender.com/) |

### Backend API (Swagger)

![Backend Swagger UI](assets/06-swagger.png)
*Fig 6 — Live backend: `GET /, /health, /reviews, /stats`, `POST /review, /review/code`, `POST /webhook/github`. Every review returns risk score (0–100), verdict (`APPROVE`/`WARNING`/`REQUEST_CHANGES`), CWE-tagged issues and suggested fixes.*

### GitHub App (PR bot)

![GitHub App listing](assets/07-github-app.png)
*Fig 7 — Public [CodeSecurityAudit App](https://github.com/apps/codesecurityaudit-app): install it on a repo and every pull request gets an automated security review — summary comment with risk score plus inline CWE findings on the exact risky lines.*

> **Status:** Dataset + RAG retrieval + review engine + GitHub PR bot **live in production** (see links above). Supervised CWE classification and LLM-grounded generation remain future work — see [What's Left](#whats-left--in-progress).

---

## 1. Problem Statement

Static analyzers flag vulnerable code but rarely explain *why* it's vulnerable in a way a developer can act on, and most public vulnerability datasets (e.g. CodeXGLUE) only carry a **binary defective/not-defective label** with no CWE, no OWASP category, and no fix guidance.

CodeSecAudit-RAG addresses this in two parts:

1. **A unified, richly-labeled vulnerability dataset** — normalizing multiple public sources into one schema carrying CWE ID, OWASP Top-10 category, severity, and vulnerability name.
2. **A Retrieval-Augmented Generation (RAG) layer** over the OWASP Cheat Sheet Series, so that a detected vulnerability can be paired with authoritative, CWE-tagged remediation guidance instead of a generic label.

---

- Dataset: https://huggingface.co/datasets/hitenvk22/CodeSecAudit-RAG-Shuffled
- Notebook: https://www.kaggle.com/code/hitenkatariya/codesecaudit-rag


## 2. What's Done

### 2.1 Dataset Engineering

Combined and normalized two public sources into one schema and published it on Hugging Face:

| Source | Type | Role |
|---|---|---|
| CodeXGLUE Defect Detection | C code, binary label only | Bulk vulnerability/non-vulnerability signal |
| OWASP Benchmark (Python) | Labeled test cases | CWE ID + OWASP category + severity ground truth |

**Dataset stats** (`hitenvk22/CodeSecAudit-RAG-Shuffled`):
- **28,548 rows total** — Train: 22.8k · Validation: 2.85k · Test: 2.88k
- Stored as auto-converted Parquet, split by `source_split`
- Unified schema per row: `id, source_name, source_type, language, framework, task, cwe_id, owasp_category, severity, is_vulnerable, vulnerability_name, input_code, fixed_code, explanation, secure_pattern, tags, metadata`

**Class distribution (EDA):**

![Top 15 CWE distribution](assets/01-cwe-distribution.png)
*Fig 1 — CWE distribution across the combined dataset. CodeXGLUE's binary-only labels dominate as `unknown`; OWASP Benchmark contributes the labeled long tail (CWE-330, CWE-643, CWE-22, CWE-328, CWE-79, etc.).*

![OWASP category distribution](assets/02-owasp-category-distribution.png)
*Fig 2 — Same imbalance viewed by OWASP Top-10 category: A02 (Cryptographic Failures), A03 (Injection), and A01 (Broken Access Control) are the best-represented labeled categories.*

> **Known limitation, called out honestly:** the `unknown` bucket (~27.3k rows) reflects CodeXGLUE's lack of CWE/OWASP labels, not an actual dominant vulnerability class. This needs to be resolved before the dataset is used for supervised CWE classification (see below).

### 2.2 RAG Corpus Construction

- Parsed and chunked the **OWASP Cheat Sheet Series** (Markdown source docs — e.g. Cryptographic Storage, File Upload, DotNet Security, GraphQL, Business Logic, HTTP Headers cheat sheets).
- Each chunk tagged with metadata: `source_file`, `cwe_id`, `title`, `section_title`.
- Embedded and indexed for similarity search.

![RAG corpus coverage by CWE](assets/05-rag-corpus-coverage.png)
*Fig 3 — Corpus coverage by CWE/security topic. Strongest coverage on CWE-89 (SQL Injection), CWE-79 (XSS), and CWE-94 (Code Injection); thinner coverage on CWE-90, CWE-502, CWE-434.*

### 2.3 Retrieval Prototype & Qualitative Testing

Built a `search_rag(query, top_k)` function and ran it against a fixed set of natural-language security questions to sanity-check retrieval quality:

```python
test_queries = [
    "How to prevent SQL injection?",
    "How to avoid eval code injection?",
    "How to store passwords securely?",
    "How to prevent SSRF?",
    "How to secure file uploads?",
]
```

![Test queries and retrieval output](assets/04-rag-test-queries.png)
*Fig 4 — Retrieval results for each test query, ranked by distance, with source cheat sheet, CWE ID, and snippet.*

![Retrieval results for SSRF and file upload](assets/03-rag-retrieval-ssrf-fileupload.png)
*Fig 5 — Close-up: top-ranked chunks correctly surface the DotNet SSRF section and File Upload Cheat Sheet sections for their respective queries, with low distance scores (0.25–0.52) indicating strong relevance.*

**Early observation:** top-1 retrieval consistently returns the topically-correct cheat sheet section (e.g. SQL injection → DotNet/GraphQL/Database Security cheat sheets; file upload → File Upload Cheat Sheet), which validates the chunking + metadata tagging strategy before investing in a generation layer on top.

---

### Used Dataset 
Here are the direct links to the official repositories and databases for the datasets and resources you listed:

**CodeXGLUE Defect Detection**

* **Link:** [github.com/microsoft/CodeXGLUE/.../Defect-detection](https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/Defect-detection)
* **Details:** Hosted in Microsoft's official CodeXGLUE repository, this specific dataset (based on the Devign framework) contains C source code used to train models to identify security defects like resource leaks and use-after-free vulnerabilities.

**OWASP Benchmark (Python)**

* **Link:** [github.com/OWASP-Benchmark](https://github.com/OWASP-Benchmark)
* **Details:** While the flagship OWASP Benchmark was originally built for Java, community ports and adaptations for Python exist under this GitHub organization to evaluate Python vulnerability detection tools.

**OWASP Cheat Sheet Series**

* **GitHub Link:** [github.com/OWASP/CheatSheetSeries](https://github.com/OWASP/CheatSheetSeries)
* **Web Link:** [cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/)
* **Details:** While this is a collection of application security guides rather than a code dataset, the raw Markdown files for the entire series are hosted openly on this GitHub repository.

**"Later Sources"**

* **Details:** This is **not a standalone dataset**. Because you are pulling from a list of security datasets, it is highly likely that you copied this from a table in a research paper or systematic review. In literature reviews, "Later Sources" is a common categorical header used to describe datasets or studies found *after* the original search protocol was conducted.

**OWASP Benchmark (Java)**

* **Link:** [github.com/OWASP/Benchmark](https://www.google.com/search?q=https://github.com/OWASP/Benchmark)
* **Details:** The official, flagship OWASP test suite. It is a fully runnable open-source Java web application designed to evaluate the speed, coverage, and accuracy of automated vulnerability detection tools.

**NIST Juliet Test Suite for Java (v1.3)**

* **Link:** [samate.nist.gov/SARD/test-suites/111](https://www.google.com/search?q=https://samate.nist.gov/SARD/test-suites/111)
* **Details:** Hosted by the NIST Software Assurance Reference Dataset (SARD) project, this contains nearly 29,000 synthetic Java programs with known, documented flaws mapped to specific Common Weakness Enumerations (CWEs).

**NIST Juliet Test Suite for C/C++ (v1.3)**

* **Link:** [samate.nist.gov/SARD/test-suites/112](https://samate.nist.gov/SARD/test-suites/112)
* **Details:** Also hosted on NIST SARD, this is the C/C++ equivalent containing thousands of test cases with intentional vulnerabilities (like buffer overflows) alongside fixed versions of the code to test tool discrimination.

## 3. What's Left / In Progress

| Area | Gap | Planned Next Step |
|---|---|---|
| Label quality | ~96% of combined dataset has `unknown` CWE/OWASP (CodeXGLUE limitation) | Either restrict supervised classification training to the OWASP-Benchmark-labeled subset, or weak-label CodeXGLUE rows via the RAG layer / a CWE classifier |
| Retrieval evaluation | Only qualitative (eyeballing top-k snippets) | Add quantitative metrics: Precision@k, Recall@k, MRR against a held-out labeled query set |
| Classification model | Not yet trained | Fine-tune a code-vulnerability classifier (e.g. CodeBERT/GraphCodeBERT) on the labeled subset, output CWE + severity |
| Generation layer | Retrieval-only right now | Add an LLM generation step that takes (flagged code + retrieved cheat-sheet chunks) → produces a plain-English explanation + fix suggestion, grounded in citations |
| End-to-end pipeline | ~~Separate notebooks~~ → **Done**: `review_engine/pipeline.py` (rules → RAG enrich → risk/verdict) + `POST /review/code` with SQLite history | Add LLM generation + classifier on top |
| Serving | ~~Notebook-only prototype~~ → **Done**: backend on Render, website on Vercel, RAG on Render (ONNX build fits 512 MB free tier) | Harden (Postgres for history, HF PRO Space as RAG alternative) |
| Testing | No formal test suite | Add unit tests for chunking, retrieval, and schema validation |
| Docs | This README is the first pass | Add data card / model card once classifier + generation land |

---

## 4. Proposed Architecture (Refactored)

### 4.1 Overall System Architecture

```mermaid
flowchart TD
    subgraph Data["1. Data Pipeline"]
        A1[CodeXGLUE Defect Detection] --> N[Normalizer]
        A2[OWASP Benchmark Python] --> N
        N --> D[(Unified Dataset<br/>HF: CodeSecAudit-RAG-Shuffled)]
    end

    subgraph Corpus["2. Knowledge Corpus Pipeline"]
        C1[OWASP Cheat Sheet Series .md] --> C2[Chunker + CWE/Title Tagging]
        C2 --> C3[Embedding Model]
        C3 --> V[(Vector Store)]
    end

    subgraph Inference["3. Inference Pipeline (proposed)"]
        I1[Input: source code snippet] --> I2[Vulnerability Classifier<br/>CWE + severity]
        I2 --> I3[Query Builder]
        I3 --> V
        V --> I4[Top-k Retrieved Chunks]
        I2 --> I5[Generation / LLM Layer]
        I4 --> I5
        I5 --> I6[Output: Explanation + Cited Fix Guidance]
    end

    D -.trains.-> I2
```

### 4.2 Data Pipeline Detail

```mermaid
flowchart LR
    subgraph Sources
        S1[CodeXGLUE<br/>~22.8k rows<br/>Binary label only]
        S2[OWASP Benchmark<br/>~5.7k rows<br/>CWE + OWASP + Severity]
    end

    subgraph Normalization
        N1[Schema Mapping]
        N2[CWE ID Extraction]
        N3[OWASP Category Mapping]
        N4[Severity Assignment]
        N5[Code + Fix Pairing]
    end

    subgraph Output
        O1[(Unified Parquet<br/>28,548 rows<br/>17 columns)]
    end

    S1 --> N1
    S2 --> N1
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
    N5 --> O1
```

### 4.3 RAG Corpus Pipeline

```mermaid
flowchart TD
    A[OWASP Cheat Sheet Series<br/>Markdown files] --> B[File Parser]
    B --> C[Section Splitter]
    C --> D[CWE ID Extractor<br/>regex + manual mapping]
    D --> E[Metadata Enrichment<br/>source_file, title, section_title]
    E --> F[Chunking<br/>~512 tokens per chunk]
    F --> G[Embedding Model<br/>ONNX MiniLM int8]
    G --> H[(In-memory index<br/>numpy cosine)]
    
    style A fill:#e1f5fe
    style H fill:#f3e5f5
```

### 4.4 Inference Pipeline (Proposed)

```mermaid
flowchart TD
    A[Source Code Input] --> B{Classifier}
    B -->|CWE ID + Severity| C[Query Builder]
    B -->|Code Features| E[CodeBERT / GraphCodeBERT]
    
    C --> D[Semantic Search<br/>Vector Store]
    D --> F[Top-k Retrieved Chunks<br/>Cheat Sheet Sections]
    
    E --> G[LLM Generation Layer]
    F --> G
    
    G --> H[Output]
    H --> I[Vulnerability Explanation]
    H --> J[Remediation Guidance]
    H --> K[Citations<br/>Cheat Sheet References]
    
    style A fill:#fff3e0
    style H fill:#e8f5e9
```

### 4.5 End-to-End Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant App as CodeSecAudit-RAG
    participant Cls as Classifier
    participant RAG as RAG Engine
    participant LLM as Generation Layer
    participant DB as Vector Store

    Dev->>App: Submit source code
    App->>Cls: Classify vulnerability
    Cls->>App: CWE ID + Severity
    App->>RAG: Query with CWE context
    RAG->>DB: Semantic search
    DB->>RAG: Top-k cheat sheet chunks
    RAG->>LLM: Code + Retrieved chunks
    LLM->>App: Explanation + Fix guidance
    App->>Dev: Annotated report with citations
```

**Design principles for the refactor:**
- **Separation of concerns** — data normalization, corpus indexing, and inference are independent, swappable modules (not notebook cells).
- **Grounded generation** — the LLM layer never answers from parametric memory alone; every explanation is backed by a retrieved, cited cheat-sheet chunk.
- **CWE as the join key** — classifier output and retrieval corpus both key off CWE ID, so the two pipelines can be developed and evaluated independently before integration.

---

## 5. Repo Structure (actual)

```
CodeSecAudit/
├── README.md
├── .env / .env.example          # single env file for all services (never committed)
├── docker-compose.yml           # backend + rag-service + website + mongo
├── Dockerfile + start-all.sh    # all-in-one single-container image
├── vercel.json + api/index.py   # website serverless entrypoint
├── render.yaml                  # Render blueprint (backend + rag-service)
├── backend/                     # FastAPI review API :8003
│   ├── api/main.py              # /, /health, /review, /review/code, /reviews, /stats, /webhook/github
│   ├── review_engine/           # critic (regex rules), pipeline, fixer, risk_score, remote_rag, github_app
│   ├── review_store/            # SQLite review history
│   ├── scripts/                 # CLI, dataset pipeline, eval, deploy helpers
│   ├── eval/golden_cases.jsonl  # engine regression cases
│   └── Dockerfile | requirements.txt | README.md
├── rag-service/                 # FastAPI retrieval API :7860
│   ├── rag_service/             # main.py, index.py (ONNX), schemas.py
│   └── Dockerfile | requirements.txt | README.md
├── website/                     # Flask SaaS site :5000
│   ├── app.py, auth.py, otp.py, email_service.py, db.py, api_client.py, ...
│   ├── templates/ | static/
│   └── Dockerfile | requirements.txt | README.md
├── assets/
│   ├── 01-cwe-distribution.png
│   ├── 02-owasp-category-distribution.png
│   ├── 03-rag-retrieval-ssrf-fileupload.png
│   ├── 04-rag-test-queries.png
│   ├── 05-rag-corpus-coverage.png
│   ├── 06-swagger.png
│   └── 07-github-app.png
├── notebooks/
│   └── codesecaudit-rag.ipynb   # research prototype (EDA + RAG experiments)
└── docs/
    └── architecture.md (+ 20 topic docs)
```

---

