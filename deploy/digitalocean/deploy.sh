#!/usr/bin/env bash
# =============================================================================
# DigitalOcean App Platform — Deployment Script for the Agentic RAG System
# =============================================================================
#
# Prerequisites:
#   1. doctl CLI installed → https://docs.digitalocean.com/reference/doctl/how-to/install/
#   2. Authenticated       → doctl auth init
#   3. Repository pushed to GitHub
#
# Usage:
#   chmod +x deploy/digitalocean/deploy.sh
#   ./deploy/digitalocean/deploy.sh
#
# After deployment, set your API key in the DigitalOcean dashboard:
#   Apps → rag-chatbot → Settings → Environment Variables
#     GOOGLE_API_KEY = your_key   (or OPENAI_API_KEY)
# =============================================================================

set -euo pipefail

SPEC_FILE="deploy/digitalocean/app.yaml"

echo "=== Agentic RAG System — DigitalOcean App Platform Deployment ==="
echo ""

# Verify doctl is installed
if ! command -v doctl &>/dev/null; then
    echo "ERROR: doctl CLI not found."
    echo "  Install → https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Verify spec file exists
if [ ! -f "$SPEC_FILE" ]; then
    echo "ERROR: Spec file not found at $SPEC_FILE"
    echo "  Run this script from the project root directory."
    exit 1
fi

echo "→ Creating app from spec: $SPEC_FILE"
doctl apps create --spec "$SPEC_FILE" --format ID,DefaultIngress --no-header

echo ""
echo "=== Deployment started! ==="
echo ""
echo "Next steps:"
echo "  1. Open the DigitalOcean dashboard → Apps"
echo "  2. Go to the 'rag-chatbot' app → Settings → Environment Variables"
echo "  3. Set GOOGLE_API_KEY (or OPENAI_API_KEY)"
echo "  4. Wait for the build to complete"
echo ""
echo "Useful commands:"
echo "  doctl apps list                    # List apps"
echo "  doctl apps logs <app-id> --type run  # View logs"
echo "  doctl apps delete <app-id>         # Delete the app"
