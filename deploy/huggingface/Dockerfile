# HuggingFace Spaces Dockerfile — Agentic RAG System
#
# HuggingFace Spaces (Docker SDK) exposes only port 7860.
# This Dockerfile runs the FastAPI backend on port 8000 internally
# and exposes the Streamlit UI on port 7860.
#
# Usage:
#   1. Create a new HF Space → choose "Docker" SDK
#   2. Copy the project files into the Space repo
#   3. Replace the root Dockerfile with this one (or copy this to the root)
#   4. Add your API key under Settings → Variables and secrets
#   5. Push to deploy

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl needed for health checks)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
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

# HuggingFace Spaces expects port 7860
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Create startup script — API on :8000 (internal), Streamlit UI on :7860 (exposed)
RUN printf '#!/bin/bash\npython main.py &\nstreamlit run rag_system/ui/streamlit_app.py --server.port 7860 --server.address 0.0.0.0\n' > start.sh && chmod +x start.sh

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./start.sh"]
