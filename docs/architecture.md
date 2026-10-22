# CodeSecAudit AI Architecture

## 1. System Topology

```mermaid
flowchart TD
    subgraph Browser Layer
        BROWSER[Browser User]
    end

    subgraph Client Service ["client (Next.js + TSX)"]
        NEXT[Next.js App Router]
        PROXY[Same-origin API Rewrite /api/*]
    end

    subgraph Main Backend ["main-server (Python + FastAPI)"]
        API[FastAPI Security Core]
        AUTH[GitHub OAuth PKCE & Sessions]
        WH[Webhook Receiver]
        AUDIT[Audit Events & RLS Isolation]
        LOGS[Sanitized Admin Logs]
    end

    subgraph Worker ["main-worker (Python + FastAPI codebase)"]
        WORKER[Background Review Processor]
        DETECTOR[Rule-based Scanner]
    end

    subgraph RAG Microservice ["rag-server (Private Network)"]
        RAG_API[FastAPI Internal Retrieval]
        EMBED[SentenceTransformer all-MiniLM-L6-v2]
    end

    subgraph Supporting Infrastructure
        PG[(PostgreSQL 16 Persistence)]
        REDIS[(Redis 7 Sessions, Queues, Logs)]
        QDRANT[(Qdrant Vector Database)]
    end

    BROWSER --> NEXT
    NEXT --> PROXY
    PROXY --> API
    API --> AUTH
    API --> WH
    API --> PG
    API --> REDIS
    WH -->|Enqueue Job 202| REDIS
    REDIS -->|Pop Job| WORKER
    WORKER --> DETECTOR
    WORKER -->|Internal HTTP + Token| RAG_API
    RAG_API --> EMBED
    RAG_API --> QDRANT
    WORKER --> PG
    WORKER --> REDIS
```

## 2. Server Responsibilities

| Server | Tech Stack | Responsibilities |
|---|---|---|
| `client` | Next.js 14 + TSX | Product UI, SSR, same-origin API proxy, display-only log viewer |
| `main-server` | FastAPI + Python 3.11 | Security boundary, GitHub App/OAuth, PostgreSQL persistence, Redis sessions/queues/rate limits, admin logs |
| `main-worker` | FastAPI codebase | Asynchronous pull request review processing, diff fetching, static checks, guidance synthesis |
| `rag-server` | FastAPI + Python 3.11 | Private embedding, indexing, Qdrant vector search over OWASP cheat sheets |

## 3. Data Ownership & Storage Boundaries

- **PostgreSQL 16:** `users`, `organizations`, `memberships`, `github_installations`, `repositories`, `webhook_deliveries`, `review_jobs`, `reviews`, `findings`, `usage_events`, `audit_events`.
- **Redis 7:** `session:{id}` (opaque sessions), `rate:{scope}:{id}`, `webhook:{delivery-id}`, `queue:review`, `log:main-server`, `log:client`, `log:rag-server`.
- **Qdrant:** `secure_guidance_v1` collection containing OWASP guidance chunks and 384-dimensional dense vectors.
