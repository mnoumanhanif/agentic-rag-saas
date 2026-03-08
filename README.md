# 🤖 Agentic RAG SaaS Platform

A production-ready **AI SaaS Platform** built around an advanced **Agentic Retrieval-Augmented Generation (RAG)** system. Upload documents, ask questions, and receive accurate, citation-backed answers powered by multi-step AI reasoning.

Unlike traditional RAG chatbots that perform a single retrieval-and-generate pass, this system uses **six specialized AI agents** that analyze queries, retrieve context through hybrid search, reason over evidence, call external tools, and self-evaluate answers — producing significantly higher-quality results.

Built with **FastAPI**, **Next.js**, **LangChain**, and **multiple LLM providers** (OpenAI, Google Gemini, Anthropic Claude, Groq, OpenRouter, Ollama), the platform supports multi-tenant knowledge bases, JWT authentication, background workers, and deployment to Docker, DigitalOcean, Azure, and HuggingFace Spaces.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Agentic RAG Pipeline](#agentic-rag-pipeline)
- [Document Ingestion Pipeline](#document-ingestion-pipeline)
- [Hybrid Retrieval System](#hybrid-retrieval-system)
- [Reranking](#reranking)
- [Context Compression](#context-compression)
- [Tool Agents](#tool-agents)
- [SaaS Platform Features](#saas-platform-features)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [Production Deployment](#production-deployment)
- [API Documentation](#api-documentation)
- [Evaluation Pipeline](#evaluation-pipeline)
- [Observability](#observability)
- [Security](#security)
- [Future Improvements](#future-improvements)

---

## System Architecture

The platform follows a layered architecture where each component has a clear responsibility. User requests flow through the frontend, pass through a reverse proxy, hit the FastAPI backend, and are processed by the Agentic RAG pipeline before returning answers with source citations.

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Next.js SaaS Frontend                           │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────────────┐   │
│  │ Auth Pages│  │ Chat UI   │  │ Knowledge │  │ Admin          │   │
│  │ Login /   │  │ Streaming │  │ Base Mgmt │  │ Dashboard      │   │
│  │ Signup    │  │ Citations │  │ Documents │  │ System Metrics │   │
│  └───────────┘  └───────────┘  └───────────┘  └────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│                       Nginx Reverse Proxy                            │
│             Rate limiting · Security headers · SSL                   │
├──────────────────────────────────────────────────────────────────────┤
│                    FastAPI Backend (SaaS API)                         │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ JWT Auth · RBAC · Multi-Tenant KBs · Conversations · Admin API │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│                     Agentic RAG Pipeline                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │   Query    │→ │ Retrieval  │→ │ Reasoning  │→ │  Reflection  │  │
│  │  Analysis  │  │   Agent    │  │   Agent    │  │    Agent     │  │
│  │   Agent    │  │            │  │            │  │              │  │
│  └────────────┘  └─────┬──────┘  └──────┬─────┘  └──────────────┘  │
│                        │                │                            │
│          ┌─────────────┴───┐    ┌───────┴────────┐                  │
│          │   Retrieval     │    │  Tool Agents   │                  │
│     ┌────┴─────┐ ┌────────┐│    │  Calculator    │                  │
│     │ Hybrid   │ │Rerank  ││    │  Web Search    │                  │
│     │ Search   │ │+ Comp- ││    │  Unit Convert  │                  │
│     │BM25+Vec  │ │ ress   ││    │  DateTime      │                  │
│     └──────────┘ └────────┘│    └────────────────┘                  │
│                            │                                         │
├──────────────────────────────────────────────────────────────────────┤
│  SQLAlchemy DB  │  Vector Store  │  Embeddings  │  LLMs  │  Redis   │
└──────────────────────────────────────────────────────────────────────┘
```

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Frontend** | Next.js 16 + React 19 | SaaS interface — chat, document management, admin dashboard |
| **Proxy** | Nginx | Rate limiting, security headers, SSL termination, request routing |
| **API** | FastAPI + Gunicorn | REST API with JWT auth, RBAC, request validation, middleware stack |
| **Pipeline** | Agentic RAG | Multi-agent query processing — analysis, retrieval, reasoning, reflection |
| **Retrieval** | Hybrid Search | BM25 keyword + dense vector search, reranking, compression |
| **Storage** | FAISS / Chroma | Vector similarity search over document embeddings |
| **Database** | SQLAlchemy (SQLite / PostgreSQL) | Users, knowledge bases, documents, conversations, analytics |
| **Queue** | Redis + RQ | Async document ingestion and background job processing |
| **LLMs** | OpenAI, Gemini, Claude, Groq, OpenRouter, Ollama | Language model inference with auto-detection |

---

## Agentic RAG Pipeline

The core of the system is a **multi-agent pipeline** where specialized agents collaborate to produce high-quality, grounded answers. Each agent has a focused responsibility and communicates results to the next stage.

```
User Query
    │
    ▼
┌──────────────────┐
│ Query Analysis   │  Classify query type (factual / analytical / conversational / creative)
│ Agent            │  Determine if retrieval is needed
│                  │  Rewrite query for optimal retrieval
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Router Agent     │  Route to retrieval strategies (dense / sparse / hybrid)
│                  │  Decide if external tools are needed
└────────┬─────────┘
         │
    ┌────┴─────────────────┐
    │                      │
    ▼                      ▼
┌──────────────┐   ┌──────────────┐
│ Retrieval    │   │ Tool Agent   │
│ Agent        │   │              │
│              │   │ Calculator   │
│ Multi-query  │   │ Web Search   │
│ Hybrid search│   │ Unit Convert │
│ Reranking    │   │ DateTime     │
│ Compression  │   └──────────────┘
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Reasoning Agent  │  Synthesize answer from retrieved context
│                  │  Chain-of-thought reasoning
│                  │  Generate source citations
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Reflection Agent │  Evaluate answer quality (0-1 confidence score)
│                  │  Detect hallucinations
│                  │  Trigger re-generation if confidence < 0.7
└────────┬─────────┘
         │
         ▼
    Final Answer
    + Sources
    + Confidence
    + Execution Steps
```

### Agent Details

| Agent | File | Responsibility |
|-------|------|----------------|
| **Query Analysis** | `agents/query_agent.py` | Classifies query type, determines retrieval needs, rewrites queries for better retrieval |
| **Router** | `agents/router_agent.py` | Routes to dense/sparse/hybrid retrieval strategies and decides when to call external tools |
| **Retrieval** | `agents/retrieval_agent.py` | Orchestrates the full retrieval pipeline — hybrid search, multi-query expansion, reranking, compression |
| **Tool** | `agents/tool_agent.py` | Executes external tools (calculator, web search, unit converter, datetime) with a registerable tool system |
| **Reasoning** | `agents/reasoning_agent.py` | Synthesizes answers using chain-of-thought reasoning with source citations and chat history awareness |
| **Reflection** | `agents/reflection_agent.py` | Self-evaluates answers for faithfulness and hallucination, triggers improvement if confidence is below threshold |

---

## Document Ingestion Pipeline

Documents enter the system through the upload API and are processed into searchable vector embeddings.

```
PDF Upload
    │
    ▼
┌──────────────────┐
│ Validation       │  Check file type, size, magic bytes, EOF marker
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Background Queue │  Redis + RQ enqueues job (falls back to sync if Redis unavailable)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PDF Loading      │  Stream pages one-by-one (memory efficient)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Text Chunking    │  Recursive text splitter — 600 tokens per chunk, 80 token overlap
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Batch Embedding  │  Encode 32 chunks at a time using sentence-transformers (all-MiniLM-L6-v2)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Vector Store     │  Index embeddings in FAISS (default) or Chroma for similarity search
└──────────────────┘
```

**Why background workers?** Document ingestion involves downloading, parsing, chunking, and embedding — which can take minutes for large PDFs. Background workers (Redis + RQ) keep the API responsive by processing uploads asynchronously. Users can poll job status via the `/jobs/{job_id}` endpoint. When Redis is unavailable, the system falls back to synchronous processing automatically.

---

## Hybrid Retrieval System

The system combines two complementary search strategies to maximize recall:

```
User Query
    │
    ├──────────────────────────────────┐
    │                                  │
    ▼                                  ▼
┌──────────────────┐       ┌──────────────────┐
│ Dense Retrieval  │       │ Sparse Retrieval  │
│                  │       │                   │
│ Encode query     │       │ BM25 keyword      │
│ with embeddings  │       │ matching          │
│                  │       │                   │
│ Cosine similarity│       │ Term frequency ×  │
│ in vector space  │       │ inverse document  │
│                  │       │ frequency         │
└────────┬─────────┘       └─────────┬─────────┘
         │                           │
         └─────────┬─────────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │ Reciprocal Rank  │
         │ Fusion (RRF)     │
         │                  │
         │ Dense weight: 0.7│
         │ Sparse weight:0.3│
         └────────┬─────────┘
                  │
                  ▼
          Merged Results
```

| Strategy | How It Works | Strength |
|----------|-------------|----------|
| **Dense Retrieval** | Encodes query and documents into embedding vectors, finds nearest neighbors by cosine similarity | Captures semantic meaning — finds relevant content even with different wording |
| **Sparse Retrieval (BM25)** | Scores documents by term frequency × inverse document frequency | Excels at exact keyword matching — important for names, codes, acronyms |
| **Reciprocal Rank Fusion** | Merges ranked lists: `score = Σ 1/(k + rank)` with configurable weights | Combines the strengths of both approaches into a single ranked list |

**Multi-Query Expansion**: Before retrieval, the system generates **3 alternative phrasings** of the user's query using the LLM, retrieves results for each, and deduplicates — significantly improving recall for ambiguous queries.

---

## Reranking

After hybrid retrieval, a **cross-encoder reranker** re-scores results for precision:

```
Top ~20 retrieved chunks
         │
         ▼
┌──────────────────────────┐
│ Cross-Encoder Reranker   │
│                          │
│ Model: ms-marco-MiniLM   │
│ -L-6-v2                  │
│                          │
│ Jointly encodes          │
│ (query, document) pairs  │
│ for accurate relevance   │
│ scoring                  │
└────────┬─────────────────┘
         │
         ▼
Top 5 most relevant chunks
```

**Why reranking matters:** Initial retrieval (BM25 + dense) is fast but uses lightweight similarity scores. The cross-encoder model reads each query-document pair together, producing much more accurate relevance judgments. This typically improves answer quality by filtering out marginally relevant results.

---

## Context Compression

Before sending context to the LLM, irrelevant text is removed to reduce token usage and improve answer focus:

```
Retrieved Documents (potentially thousands of tokens)
         │
         ▼
┌──────────────────────────────────┐
│ Context Compressor               │
│                                  │
│ 1. Split into sentences          │
│ 2. Score each sentence by        │
│    query term overlap            │
│ 3. Select top-scoring sentences  │
│    within 500 token budget       │
│ 4. Fall back to truncation       │
│    if no sentences match         │
└────────┬─────────────────────────┘
         │
         ▼
Compressed Context (~500 tokens per document)
```

**Techniques used:**
- **Sentence-level scoring** — splits documents into sentences and ranks by query term overlap
- **Token budget enforcement** — limits each document to 500 tokens maximum
- **Fallback truncation** — if no sentence scores above zero, truncates to the token limit

This reduces LLM token consumption and prevents the model from being distracted by irrelevant passages.

---

## Tool Agents

When a query requires information beyond the document knowledge base, the system can call **external tools**:

| Tool | Capability | Example |
|------|-----------|---------|
| **Calculator** | Safe math evaluation with scientific functions (sqrt, sin, cos, log, pow, etc.) | `"What is sqrt(144) + 15^2?"` |
| **Web Search** | DuckDuckGo Instant Answer API — no API key required | `"What is the latest news about AI regulation?"` |
| **Unit Converter** | Converts between 10 unit pairs (km↔miles, kg↔lbs, °C↔°F, m↔ft, L↔gal) | `"Convert 100 km to miles"` |
| **DateTime** | Returns current UTC date and time | `"What time is it?"` |

**How agents decide when to use tools:**

The **Router Agent** analyzes each query and determines whether it can be answered from the knowledge base or requires an external tool. For example:
- A math expression triggers the **calculator**
- A question about current events triggers **web search**
- A unit conversion request triggers the **unit converter**
- Questions about time trigger the **datetime** tool

Tools are registered in a **tool registry** — new tools can be added via `register_tool(name, func, description)`.

---

## SaaS Platform Features

The platform operates as a full **multi-tenant SaaS application**:

| Feature | Description |
|---------|-------------|
| **JWT Authentication** | Signup, login, token refresh, password reset with bcrypt hashing |
| **Role-Based Access Control** | Admin and user roles with separate permissions |
| **Multi-Tenant Knowledge Bases** | Each user creates isolated knowledge bases with their own documents |
| **Document Management** | Upload, list, delete PDFs per knowledge base |
| **Persistent Conversations** | Chat history stored in database with message metadata |
| **Admin Dashboard** | System metrics, user management, role assignment, active/inactive toggling |
| **Analytics** | Per-user query analytics — daily breakdowns, latency, token usage |
| **Dark/Light Mode** | Theme switching in the frontend UI |

### Database Models

The SQLAlchemy ORM defines six core models:

| Model | Purpose |
|-------|---------|
| `User` | Multi-tenant users with roles (admin/user), password hash, active status |
| `KnowledgeBase` | Per-user document collections with name and description |
| `Document` | Tracks uploaded files with ingestion status (queued/processing/completed/failed) |
| `Conversation` | Multi-turn chat sessions with pinning support |
| `Message` | Individual Q&A pairs with metadata (sources, execution steps, latency, tokens) |
| `AnalyticsEvent` | Usage tracking for queries, uploads, and errors |

---

## Technology Stack

### Frontend

| Technology | Role |
|-----------|------|
| **Next.js 16** | React framework with App Router, API routes, and server-side rendering |
| **React 19** | UI component library |
| **TypeScript** | Type-safe frontend code |
| **Tailwind CSS v4** | Utility-first CSS styling |
| **shadcn/ui** (Radix UI) | Accessible, reusable UI primitives (dialogs, tabs, forms, tooltips) |
| **Zustand** | Lightweight state management for auth and chat state |
| **Framer Motion** | Smooth UI animations and transitions |
| **React Markdown** | Render markdown answers with GFM support and syntax highlighting |
| **Recharts** | Analytics charts in the admin dashboard |
| **TanStack React Query** | Server state management and data fetching |
| **Lucide React** | Icon library |

### Backend

| Technology | Role |
|-----------|------|
| **FastAPI** | High-performance async Python API framework with automatic OpenAPI docs |
| **Pydantic v2** | Request/response validation, data models with HTML escaping |
| **LangChain** | LLM orchestration, prompt templates, document processing |
| **SQLAlchemy 2.0** | ORM for database models with connection pooling |
| **PyJWT** | JWT token creation and verification (HS256) |
| **Passlib + Bcrypt** | Secure password hashing |

### AI & Retrieval

| Technology | Role |
|-----------|------|
| **sentence-transformers** | Embedding model (`all-MiniLM-L6-v2`, 384 dimensions) |
| **FAISS** | In-memory vector similarity search (default) |
| **ChromaDB** | Persistent vector store alternative |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | Cross-encoder reranking model |
| **rank-bm25** | BM25 sparse retrieval implementation |

### LLM Providers

| Provider | Model (Default) | Notes |
|----------|----------------|-------|
| **OpenRouter** | `arcee-ai/trinity-large-preview:free` | Default — access 100+ models with one key |
| **Google Gemini** | `gemini-2.0-flash` | Free tier available |
| **OpenAI** | `gpt-4o-mini` | GPT family |
| **Anthropic** | `claude-sonnet-4-20250514` | Claude family |
| **Groq** | `llama-3.3-70b-versatile` | Fast inference |
| **Ollama** | `llama3` | Fully local — no API key needed |

The system **auto-detects** which provider to use based on which API key is set in your environment.

### Infrastructure

| Technology | Role |
|-----------|------|
| **Redis** | Cache layer (TTL 3600s) and task queue broker |
| **RQ (Redis Queue)** | Background job processing for document ingestion |
| **Gunicorn** | Production WSGI server with Uvicorn workers |
| **Nginx** | Reverse proxy with rate limiting and security headers |
| **Docker** | Containerization for all services |
| **Docker Compose** | Multi-service orchestration (dev and production configs) |

---

## Repository Structure

```
rag-chatbot/
├── frontend/                          # Next.js SaaS Frontend
│   └── src/
│       ├── app/                       # App Router pages & API route handlers
│       │   └── api/                   # Upload and query proxy routes
│       ├── components/
│       │   ├── auth/                  # Login / signup forms
│       │   ├── admin/                 # Admin dashboard panel
│       │   ├── chat/                  # Chat interface (messages, input, area)
│       │   ├── dashboard/             # Analytics dashboard view
│       │   ├── documents/             # Document upload & management
│       │   ├── layout/                # Header and sidebar navigation
│       │   └── ui/                    # Reusable UI primitives (shadcn/ui style)
│       ├── hooks/                     # Zustand stores (auth, chat) & custom hooks
│       ├── lib/                       # API client configuration
│       ├── services/                  # API client with typed endpoints
│       └── types/                     # TypeScript type definitions
│
├── rag_system/                        # Python Backend
│   ├── agents/                        # Six specialized AI agents
│   │   ├── query_agent.py             # Query classification & rewriting
│   │   ├── router_agent.py            # Strategy routing & tool selection
│   │   ├── retrieval_agent.py         # Retrieval orchestration
│   │   ├── reasoning_agent.py         # Answer synthesis with citations
│   │   ├── reflection_agent.py        # Self-evaluation & hallucination detection
│   │   └── tool_agent.py              # External tool execution
│   ├── retrievers/                    # Six retrieval strategies
│   │   ├── dense_retriever.py         # Vector similarity search
│   │   ├── sparse_retriever.py        # BM25 keyword matching
│   │   ├── hybrid_retriever.py        # Reciprocal Rank Fusion (dense + sparse)
│   │   ├── reranker.py                # Cross-encoder reranking
│   │   ├── multi_query_retriever.py   # Query expansion (3 variants)
│   │   └── context_compressor.py      # Sentence-level compression
│   ├── pipelines/                     # Core processing pipelines
│   │   ├── agentic_rag_pipeline.py    # Main agent orchestration pipeline
│   │   └── ingestion_pipeline.py      # Document loading, chunking, embedding
│   ├── api/                           # FastAPI application
│   │   ├── server.py                  # App factory with middleware stack
│   │   ├── models.py                  # Pydantic request/response schemas
│   │   ├── security.py                # Prompt injection detection & sanitization
│   │   ├── middleware.py              # Request logging, IP throttling, rate limiting
│   │   └── routes/                    # SaaS API route modules
│   │       ├── auth.py                # Signup, login, token refresh
│   │       ├── knowledge_bases.py     # Knowledge base CRUD
│   │       ├── conversations.py       # Conversation & message management
│   │       ├── documents.py           # Document upload & management
│   │       ├── admin.py               # Admin metrics, user management
│   │       └── observability.py       # Prometheus metrics, detailed health
│   ├── auth/                          # Authentication system
│   │   ├── jwt_handler.py             # JWT creation, verification, password hashing
│   │   └── dependencies.py            # FastAPI dependencies (get_current_user, require_admin)
│   ├── database/                      # Database layer
│   │   ├── engine.py                  # SQLAlchemy engine & session factory
│   │   └── models.py                  # ORM models (User, KnowledgeBase, Document, etc.)
│   ├── config/                        # Centralized configuration
│   │   └── settings.py                # All settings classes (LLM, embedding, retrieval, security)
│   ├── embeddings/                    # Embedding model factory
│   │   └── embedding_factory.py       # SentenceTransformer initialization & batch encoding
│   ├── vectorstores/                  # Vector store factory
│   │   └── vectorstore_factory.py     # FAISS / Chroma initialization
│   ├── evaluation/                    # RAG quality evaluation
│   │   ├── evaluator.py               # Single & benchmark evaluation
│   │   └── metrics.py                 # Recall@k, faithfulness, relevance, correctness
│   ├── prompts/                       # LLM prompt templates
│   │   └── templates.py               # 7 prompt templates for all agent operations
│   ├── workers/                       # Background job processing
│   │   └── tasks.py                   # RQ task definitions & fallback sync processing
│   └── utils/                         # Production utilities
│       └── resilience.py              # Circuit breaker, retry with backoff, fallback
│
├── tests/                             # Test suite (12 modules)
│   ├── conftest.py                    # Shared pytest fixtures
│   ├── test_api.py                    # API endpoint tests
│   ├── test_agents.py                 # Agent initialization & behavior
│   ├── test_retrievers.py             # Retrieval strategy tests
│   ├── test_config.py                 # Configuration & provider detection
│   ├── test_security.py               # Prompt injection & security tests
│   ├── test_resilience.py             # Circuit breaker & retry logic
│   ├── test_saas.py                   # Multi-tenant auth & KB isolation
│   ├── test_models.py                 # ORM model tests
│   ├── test_evaluation.py             # Evaluation metric tests
│   ├── test_evaluator.py              # Benchmark evaluation tests
│   └── test_router_and_workers.py     # Job queuing & status tracking
│
├── deploy/                            # Cloud deployment configurations
│   ├── digitalocean/app.yaml          # DigitalOcean App Platform spec
│   ├── azure/deploy.sh                # Azure Container Apps deployment script
│   └── huggingface/Dockerfile         # HuggingFace Spaces Dockerfile
│
├── nginx/nginx.conf                   # Production Nginx reverse proxy config
├── docker-compose.yml                 # Development — single container
├── docker-compose.prod.yml            # Production — Nginx + backend + frontend + Redis + worker
├── Dockerfile                         # All-in-one Docker image
├── Dockerfile.backend                 # Production backend image (Gunicorn + Uvicorn)
├── Dockerfile.frontend                # Production frontend image (Next.js standalone)
├── gunicorn.conf.py                   # Gunicorn production configuration
├── main.py                            # Application entry point
├── requirements.txt                   # Python production dependencies
├── requirements-dev.txt               # Python dev/test dependencies
└── .env.example                       # Environment variable template
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- At least one LLM API key (or [Ollama](https://ollama.com) for local models)

### 1. Clone the Repository

```bash
git clone https://github.com/k190462/rag-chatbot.git
cd rag-chatbot
```

### 2. Set Up the Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set at least one LLM API key, for example:
# GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Start the API Server

```bash
python main.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### 4. Set Up the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 5. Use the System

1. **Sign up** — Create an account via the frontend or `POST /auth/signup`
2. **Create a knowledge base** — Organize your documents into collections
3. **Upload documents** — Upload PDF files to your knowledge base
4. **Ask questions** — Query the system and receive answers with source citations

### Docker Quick Start

For a one-command setup:

```bash
docker compose up --build
```

This starts the full system (API on port 8000, frontend on port 3000).

---

## Production Deployment

### Docker Compose (Recommended)

The production setup uses five services behind an Nginx reverse proxy:

```bash
# Set environment variables
cp .env.example .env
# Edit .env with production values

# Start production services
docker compose -f docker-compose.prod.yml up -d

# Monitor logs
docker compose -f docker-compose.prod.yml logs -f backend

# Check service health
docker compose -f docker-compose.prod.yml ps
```

**Production services:**

| Service | Port | Description |
|---------|------|-------------|
| `nginx` | 80 | Reverse proxy — rate limiting, security headers |
| `backend` | 8000 (internal) | FastAPI with Gunicorn (2+ Uvicorn workers, 2GB memory limit) |
| `frontend` | 3000 (internal) | Next.js standalone (512MB memory limit) |
| `redis` | 6379 (internal) | Cache and task queue (128MB max, LRU eviction) |
| `worker` | — | RQ background worker for document ingestion (2GB memory limit) |

### DigitalOcean App Platform

```bash
# Deploy via DigitalOcean dashboard using deploy/digitalocean/app.yaml
# Minimum: professional-s instance (1GB RAM)
# Auto-deploys on push to main branch
```

### Azure Container Apps

```bash
cd deploy/azure
chmod +x deploy.sh
./deploy.sh
# Creates: Resource Group → ACR → Container App (1 CPU, 2GB RAM, 0-3 replicas)
```

### HuggingFace Spaces

```bash
# Use deploy/huggingface/Dockerfile
# Upload to a new HuggingFace Space with Docker SDK
# Exposes port 7860 (HuggingFace requirement)
```

### Server Configuration Notes

- **Gunicorn**: Auto-scales workers (min 2), 120s timeout for LLM inference, 1000 max requests per worker to prevent memory leaks
- **Nginx**: 30 req/s API rate limit, 5 req/s upload limit, 50MB upload size, blocks `/docs` and `/redoc` in production
- **Docker**: CPU-only PyTorch to avoid 2GB CUDA libraries, embedding model pre-downloaded during build to prevent runtime OOM

---

## API Documentation

The full interactive API documentation is available at `/docs` (Swagger UI) when the server is running.

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/auth/signup` | Register a new user |
| `POST` | `/auth/login` | Login and receive JWT tokens |
| `POST` | `/auth/refresh` | Refresh access token |
| `POST` | `/auth/password-reset` | Request password reset |

### Protected Endpoints (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload PDF for ingestion |
| `GET` | `/jobs/{job_id}` | Check background job status |
| `POST` | `/query` | Query the Agentic RAG system |
| `POST` | `/evaluate` | Run RAG evaluation benchmark |

### SaaS Endpoints (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/knowledge-bases` | Create a knowledge base |
| `GET` | `/knowledge-bases` | List user's knowledge bases |
| `PUT` | `/knowledge-bases/{kb_id}` | Update a knowledge base |
| `DELETE` | `/knowledge-bases/{kb_id}` | Delete a knowledge base |
| `POST` | `/knowledge-bases/{kb_id}/documents/upload` | Upload document to KB |
| `GET` | `/knowledge-bases/{kb_id}/documents` | List KB documents |
| `DELETE` | `/knowledge-bases/{kb_id}/documents/{doc_id}` | Delete a document |
| `POST` | `/conversations` | Create a conversation |
| `GET` | `/conversations` | List user's conversations |
| `POST` | `/conversations/{id}/messages` | Send a message |
| `GET` | `/conversations/{id}/messages` | Get conversation messages |

### Admin Endpoints (Admin Role Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/metrics` | System-wide metrics |
| `GET` | `/admin/users` | List all users |
| `PATCH` | `/admin/users/{id}/role` | Change user role |
| `PATCH` | `/admin/users/{id}/toggle-active` | Toggle user status |
| `GET` | `/analytics/queries` | Per-user query analytics |

### Example: Query the RAG System

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your_password"}' \
  | jq -r '.access_token')

# Upload a document
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"

# Query the system
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the key findings in this document?",
    "chat_history": []
  }'
```

### Example: Observability

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Detailed health check
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/detailed
```

---

## Evaluation Pipeline

The system includes a built-in evaluation framework to measure RAG quality across four dimensions:

| Metric | What It Measures | How It Works |
|--------|-----------------|--------------|
| **Recall@K** | Retrieval completeness | Fraction of relevant documents found in the top-K retrieved results |
| **Faithfulness** | Answer grounding | Token overlap between the answer and source context (ignoring stopwords) |
| **Context Relevance** | Retrieval precision | Query term overlap with retrieved context |
| **Answer Correctness** | Accuracy | F1 score comparing answer tokens against a reference answer |

### Running an Evaluation

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_cases": [
      {
        "question": "What is the main topic?",
        "reference_answer": "The main topic is...",
        "relevant_doc_ids": ["doc1", "doc2"]
      }
    ]
  }'
```

The evaluation returns individual scores per test case plus aggregate averages for benchmarking.

---

## Observability

The platform provides multiple observability layers:

| Capability | Implementation |
|------------|----------------|
| **Prometheus Metrics** | `GET /metrics` — request counts, error rates, query latency, upload counts |
| **Detailed Health** | `GET /health/detailed` — total requests, avg query latency, error counts |
| **Request ID Tracing** | Every request gets a unique correlation ID via `RequestIDMiddleware` |
| **Structured Logging** | Request/response logging with method, path, status code, duration |
| **Admin Analytics** | `GET /admin/metrics` — users, KBs, documents, conversations, 24h query stats |
| **Per-User Analytics** | `GET /analytics/queries` — daily query breakdowns, latency, token usage |
| **Pipeline Execution Steps** | Each query response includes detailed agent execution steps with timing |

---

## Security

The platform implements defense-in-depth security:

| Layer | Feature |
|-------|---------|
| **Authentication** | JWT tokens (HS256) — 60 min access, 7 day refresh |
| **Password Security** | Bcrypt hashing with salt |
| **Role-Based Access Control** | Admin/user roles with middleware enforcement |
| **Prompt Injection Detection** | 17 known injection patterns blocked (jailbreak, DAN, ignore instructions, etc.) |
| **Input Sanitization** | HTML escaping, control character removal on all inputs |
| **API Key Auth** | Optional `X-API-Key` header validation for API consumers |
| **Rate Limiting** | IP-based (120 req/min), endpoint-based, Nginx layer (30 req/s) |
| **Security Headers** | HSTS, X-Content-Type-Options, X-Frame-Options, CSP, Permissions-Policy |
| **CORS Protection** | Configurable allowed origins |
| **File Upload Validation** | Magic bytes check, EOF marker validation, file size limits |
| **SQL Injection Prevention** | SQLAlchemy ORM parameterized queries |
| **Circuit Breakers** | Fail-fast for external service failures (5 failures → 60s open) |
| **Retry with Backoff** | Exponential backoff for transient failures (max 3 retries) |

---

## Future Improvements

| Area | Enhancement |
|------|------------|
| **GraphRAG** | Knowledge graph construction for multi-hop reasoning over document relationships |
| **Multi-Hop Retrieval** | Chain multiple retrieval steps to answer complex, multi-part questions |
| **Memory Agents** | Persistent agent memory across sessions for personalized responses |
| **Streaming Responses** | Server-Sent Events for real-time token streaming |
| **Knowledge Graphs** | Entity extraction and relationship mapping from ingested documents |
| **Multi-Modal RAG** | Support for images, tables, and charts in documents |
| **Fine-Tuned Embeddings** | Domain-specific embedding models for improved retrieval |
| **Advanced Caching** | Semantic cache for similar queries to reduce LLM calls |
| **WebSocket Chat** | Real-time bidirectional chat communication |
| **Plugin System** | User-installable tool plugins for domain-specific capabilities |

---

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/test_saas.py -v          # SaaS platform tests
python -m pytest tests/test_security.py -v       # Security tests
python -m pytest tests/test_resilience.py -v     # Resilience pattern tests
python -m pytest tests/test_agents.py -v         # Agent tests
python -m pytest tests/test_retrievers.py -v     # Retrieval tests
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | One LLM key required | — | Google Gemini API key |
| `OPENAI_API_KEY` | One LLM key required | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | One LLM key required | — | Anthropic API key |
| `GROQ_API_KEY` | One LLM key required | — | Groq API key |
| `OPENROUTER_API_KEY` | One LLM key required | — | OpenRouter API key |
| `OLLAMA_BASE_URL` | No | — | Ollama server URL for local models |
| `JWT_SECRET_KEY` | Yes (production) | `change-me-in-production` | Secret for JWT signing |
| `DATABASE_URL` | No | `sqlite:///rag_saas.db` | SQLAlchemy database URL |
| `REDIS_URL` | No | — | Redis connection URL |
| `WORKER_ENABLED` | No | `false` | Enable async background workers |
| `REQUIRE_API_KEY` | No | `false` | Require API key for protected endpoints |
| `API_KEYS` | No | — | Comma-separated valid API keys |
| `GUNICORN_WORKERS` | No | `2` | Number of Gunicorn workers |

---

## License

This project is open source. See the repository for license details.
