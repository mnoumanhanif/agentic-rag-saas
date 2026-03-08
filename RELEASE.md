# Release: v2.0.0 — Agentic RAG SaaS Platform

<!-- Copy everything below this line into the GitHub "Create Release" page -->
<!-- Tag: v2.0.0 -->
<!-- Title: v2.0.0 — Agentic RAG SaaS Platform -->

## Overview

This release marks the evolution of the project from a simple RAG chatbot into a **production-ready Agentic Retrieval-Augmented Generation (RAG) SaaS platform**. The system now features a modular multi-agent architecture, hybrid retrieval, self-evaluation capabilities, multi-tenant SaaS infrastructure, and deployment-ready configurations for multiple cloud platforms.

---

## ✨ Major Features

### 🤖 Agentic RAG Architecture
Six specialized AI agents collaborate in a structured pipeline to deliver high-quality, grounded answers:
- **Query Analysis Agent** — Classifies queries by type and complexity, rewrites them for optimal retrieval
- **Router Agent** — Dynamically selects retrieval strategies and tool usage based on query analysis
- **Retrieval Agent** — Orchestrates multi-strategy document retrieval with hybrid search
- **Reasoning Agent** — Synthesizes answers using chain-of-thought reasoning with source citations
- **Reflection Agent** — Self-evaluates answers for hallucinations, scoring faithfulness and completeness
- **Tool Agent** — Executes built-in tools (calculator, web search, unit converter, date/time) and supports custom tools

### 🔍 Hybrid Retrieval System
- **BM25 Sparse Search** — Term frequency–based keyword matching
- **Dense Vector Search** — Semantic similarity using sentence-transformers (`all-MiniLM-L6-v2`)
- **Reciprocal Rank Fusion** — Combines sparse and dense results with configurable weights (BM25: 0.3, Dense: 0.7)
- **Multi-Query Expansion** — Generates 3+ query variants for improved recall
- **Cross-Encoder Reranking** — Precision reranking with `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Context Compression** — Extracts query-relevant sentences to reduce noise before generation

### 🏢 Multi-Tenant SaaS Platform
- **User Management** — Signup, login, JWT authentication (access + refresh tokens), role-based access control
- **Knowledge Bases** — Isolated document collections per user with status tracking
- **Conversations** — Persistent chat sessions with message history and context preservation
- **Analytics** — Event tracking and system observability
- **Admin Dashboard** — User management, system statistics, and configuration endpoints

### 🧠 Multi-Provider LLM Support
Seamless auto-detection and switching between providers:
- OpenAI (GPT-3.5-turbo, GPT-4)
- Google Gemini (gemini-2.5-flash)
- Anthropic Claude (claude-sonnet-4-20250514)
- Groq (llama-3.3-70b-versatile)
- OpenRouter (google/gemini-2.5-flash)
- Ollama (local llama3)

### 📊 Evaluation Pipeline
Built-in RAG quality assessment with four dimensions:
- **Faithfulness** — Answer grounding in retrieved context
- **Context Relevance** — Semantic alignment between query and retrieved documents
- **Answer Correctness** — Comparison with reference answers
- **Retrieval Recall@k** — Document retrieval precision

### 🔒 Production Security
- Prompt injection detection and blocking
- API key authentication (`X-API-Key` header)
- Per-IP rate limiting with stricter mutation endpoint throttling
- Security headers (X-Content-Type-Options, X-Frame-Options, HSTS, X-XSS-Protection)
- Request ID tracing for observability
- Circuit breaker and retry patterns for external service resilience

### ⚙️ Background Processing
- Redis + RQ worker queue for async document ingestion
- Job status tracking (queued → processing → completed/failed)
- Graceful fallback to synchronous processing when Redis is unavailable

---

## 🏗️ Architecture Improvements

### RAG Pipeline Stages
```
Query → Query Analysis → Query Rewriting → Hybrid Retrieval → Reranking → Context Compression → Reasoning → Reflection → Response
```

1. **Query Analysis** — Classifies query type (factual, analytical, conversational, creative) and assesses complexity
2. **Query Rewriting** — Optimizes the query for retrieval using contextual rewriting and multi-query expansion
3. **Hybrid Retrieval** — Combines BM25 and dense vector search with reciprocal rank fusion
4. **Reranking** — Cross-encoder model jointly encodes query–document pairs for precision improvement
5. **Context Compression** — Extracts relevant sentences to reduce noise and fit context windows
6. **Reasoning** — Chain-of-thought synthesis with source citations
7. **Reflection** — Self-evaluation scoring faithfulness, completeness, and clarity; hallucination detection

### Infrastructure Improvements
- **Redis Worker Queue** — Decoupled document ingestion from API request cycle
- **Async Ingestion Pipeline** — Background processing with job tracking and progress reporting
- **Vector Database Integration** — Factory pattern supporting FAISS and Chroma with persistence
- **Docker Deployment** — Multi-stage builds with CPU-only PyTorch for optimized images
- **Nginx Reverse Proxy** — Rate limiting, security headers, upstream load balancing
- **Gunicorn WSGI** — Production worker management with health checks
- **Database Layer** — SQLAlchemy 2.0 ORM with 6 models and migration-ready schema

---

## 🛠️ Technology Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 16 | React framework with App Router |
| React | 19 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 4 | Utility-first styling |
| shadcn/ui | — | Component library (Radix UI primitives) |
| Zustand | 5 | State management |
| TanStack Query | 5 | Server state and caching |
| Framer Motion | — | Animations |
| Recharts | 3 | Dashboard charts |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | ≥0.104 | Async web framework |
| Pydantic | ≥2.5 | Data validation |
| Gunicorn | — | Production WSGI server |
| SQLAlchemy | ≥2.0 | ORM and database layer |
| PyJWT | ≥2.7 | JWT authentication |

### AI & Retrieval
| Technology | Version | Purpose |
|------------|---------|---------|
| LangChain | ≥0.3 | LLM orchestration |
| sentence-transformers | ≥2.2 | Embedding models |
| FAISS | ≥1.7 | Vector similarity search |
| ChromaDB | ≥0.4 | Vector database |
| cross-encoder | — | Reranking models |
| PyPDF | ≥3.17 | PDF document processing |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Redis + RQ | Background job queue |
| Docker | Containerization |
| Docker Compose | Service orchestration |
| Nginx | Reverse proxy and load balancing |
| SQLite / PostgreSQL | Relational data storage |

---

## 🚀 Deployment Options

| Platform | Method | Configuration |
|----------|--------|---------------|
| **Docker** | Single container | `Dockerfile` |
| **Docker Compose** | Multi-service (dev) | `docker-compose.yml` |
| **Docker Compose** | Multi-service (prod) | `docker-compose.prod.yml` |
| **HuggingFace Spaces** | Docker-based Spaces | `deploy/huggingface/` |
| **Azure Container Apps** | Autoscaling (0–3 replicas) | `deploy/azure/deploy.sh` |
| **DigitalOcean App Platform** | Managed deployment | `deploy/digitalocean/app.yaml` |
| **DigitalOcean Droplet** | Manual deployment | `deploy/digitalocean/deploy.sh` |

### Quick Start
```bash
# Clone and run with Docker
git clone https://github.com/k190462/rag-chatbot.git
cd rag-chatbot
cp .env.example .env
# Add your LLM API key to .env
docker compose up --build
```

---

## 📝 Upgrade Notes

- This is the first official release of the Agentic RAG SaaS platform (v2.0.0).
- The backend version (`rag_system/__init__.py`) is set to `2.0.0` reflecting the architectural evolution from the original RAG chatbot.
- **Minimum requirements:** Python 3.11+, Node.js 20+, 1 GB RAM (DigitalOcean professional-s or equivalent).
- **Default LLM provider:** OpenRouter with `google/gemini-2.5-flash`. Set `LLM_PROVIDER` and the corresponding API key in `.env` to use a different provider.
- **Database:** Defaults to SQLite for development. Set `DATABASE_URL` for PostgreSQL in production.
- **Redis:** Optional. The system falls back to synchronous document ingestion when Redis is unavailable.

---

## 📦 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for the complete list of changes.

---

**Suggested commit message:**
```
chore: prepare v2.0.0 release — Agentic RAG SaaS Platform
```

**Suggested tag:**
```
v2.0.0
```
