# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] — 2026-03-08

### Added

- **Agentic RAG Pipeline** — Multi-agent orchestration with six specialized AI agents (Query Analysis, Retrieval, Reasoning, Reflection, Router, and Tool agents)
- **Hybrid Retrieval System** — Combined BM25 sparse search and dense vector similarity search with reciprocal rank fusion
- **Cross-Encoder Reranking** — Precision-focused reranking using `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Context Compression** — Noise reduction by extracting query-relevant sentences before answer generation
- **Multi-Query Expansion** — Automatic generation of query variants for improved recall
- **Reflection and Hallucination Detection** — Self-evaluation agent that scores faithfulness, completeness, and clarity of generated answers
- **Tool Agents** — Built-in tools (calculator, web search, unit converter, date/time) with support for custom tool registration
- **Next.js SaaS Frontend** — Modern dashboard built with Next.js 16, React 19, TypeScript, Tailwind CSS, and shadcn/ui components
- **Multi-Tenant SaaS Architecture** — User accounts, knowledge base isolation, conversations, and analytics events via SQLAlchemy ORM
- **JWT Authentication** — Secure signup, login, token refresh, and role-based access control (admin/user)
- **FastAPI Backend** — Production-grade API with Pydantic validation, OpenAPI documentation, and Gunicorn WSGI server
- **Background Ingestion Workers** — Redis + RQ-based async document processing with job tracking and synchronous fallback
- **Evaluation Pipeline** — RAG quality metrics including faithfulness, context relevance, answer correctness, and retrieval recall@k
- **Multi-Provider LLM Support** — Auto-detection and seamless switching between OpenAI, Google Gemini, Anthropic Claude, Groq, OpenRouter, and Ollama
- **Prompt Injection Detection** — Security middleware that detects and blocks common prompt injection patterns
- **API Key Authentication** — Optional API key enforcement via `X-API-Key` header for public-facing deployments
- **Rate Limiting** — Per-IP request throttling with stricter limits on mutation endpoints
- **Security Headers Middleware** — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, and HSTS headers
- **Circuit Breaker and Retry Patterns** — Resilience utilities for wrapping external service calls with exponential backoff and fallback handling
- **Observability Routes** — Logging, tracing, and metrics collection API endpoints
- **Admin Dashboard API** — User management, system analytics, and configuration endpoints

### Improved

- **Retrieval Architecture** — Upgraded from single-strategy retrieval to a modular hybrid system with configurable BM25/dense weights
- **Query Understanding** — Added query classification (factual, analytical, conversational, creative) and complexity assessment before retrieval
- **Answer Quality** — Chain-of-thought reasoning with source citations and self-evaluation loop
- **Configuration Management** — Centralized dataclass-based settings with environment variable support and provider auto-detection
- **Embedding Strategy** — Lazy-loaded sentence-transformers with factory pattern supporting HuggingFace and OpenAI providers
- **Vector Store Abstraction** — Factory pattern supporting FAISS and Chroma with persistence and checkpoint recovery

### Refactored

- **Project Structure** — Reorganized into modular packages: agents, retrievers, pipelines, api, database, auth, config, evaluation, workers, embeddings, vectorstores, and utils
- **Pipeline Architecture** — Separated ingestion and query pipelines with clear boundaries and dependency injection
- **API Layer** — Split monolithic API into dedicated route modules (auth, conversations, knowledge bases, documents, admin, observability)

### Infrastructure

- **Docker** — Multi-stage builds with separate Dockerfile.backend and Dockerfile.frontend; CPU-only PyTorch for optimized image size
- **Docker Compose** — Development (`docker-compose.yml`) and production (`docker-compose.prod.yml`) configurations
- **Nginx Reverse Proxy** — Rate limiting zones, security headers, upstream load balancing, and route-specific throttling
- **Gunicorn** — Production WSGI configuration with worker management
- **DigitalOcean Deployment** — App Platform spec (`app.yaml`) and deployment script with professional-s tier support
- **Azure Deployment** — Container Apps deployment with autoscaling (0–3 replicas)
- **HuggingFace Spaces** — Docker-based Spaces deployment with Streamlit UI
- **Redis Integration** — Background job queue for async document ingestion with graceful fallback

### Documentation

- **Comprehensive README** — 42 KB documentation covering architecture, deployment, API reference, evaluation, and security
- **Environment Template** — `.env.example` with all configurable settings
- **Deployment Guides** — Platform-specific instructions for Docker, DigitalOcean, Azure, and HuggingFace Spaces

[2.0.0]: https://github.com/k190462/rag-chatbot/releases/tag/v2.0.0
