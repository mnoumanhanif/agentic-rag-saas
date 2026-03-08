# ── Stage 1: Build the Next.js frontend ──────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN mkdir -p public
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ── Stage 2: Python runtime ─────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl needed for HEALTHCHECK, nodejs for Next.js)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (avoids pulling ~2 GB of CUDA/NVIDIA libs)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rag_system ./rag_system
COPY main.py .

# Pre-download the sentence-transformers model so it is cached in the image.
# This avoids a runtime download that can cause OOM on memory-constrained hosts.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy built frontend (standalone output)
COPY --from=frontend-build /build/.next/standalone ./frontend-server
COPY --from=frontend-build /build/.next/static ./frontend-server/.next/static
COPY --from=frontend-build /build/public ./frontend-server/public

# Create startup script
# Runs FastAPI backend on 8000 and Next.js frontend on 3000
RUN printf '#!/bin/bash\npython main.py &\ncd frontend-server && PORT=3000 HOSTNAME=0.0.0.0 node server.js &\nstreamlit run rag_system/ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0\n' > start.sh && chmod +x start.sh

# Expose ports
EXPOSE 3000
EXPOSE 8000
EXPOSE 8501

# Health check (generous start-period for model loading on first request)
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./start.sh"]
