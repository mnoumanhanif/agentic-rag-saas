#!/usr/bin/env bash
# =============================================================================
# Azure Container Apps — Deployment Script for the Agentic RAG System
# =============================================================================
#
# Prerequisites:
#   1. Azure CLI installed        → https://learn.microsoft.com/cli/azure/install-azure-cli
#   2. Logged in                  → az login
#   3. Docker installed           → docker --version
#   4. Set your API key below or export it before running this script.
#
# Usage:
#   chmod +x deploy/azure/deploy.sh
#   export GOOGLE_API_KEY="your-key"    # or OPENAI_API_KEY
#   ./deploy/azure/deploy.sh
#
# What this script does:
#   1. Creates a resource group
#   2. Creates an Azure Container Registry (ACR)
#   3. Builds and pushes the Docker image to ACR
#   4. Creates a Container Apps environment
#   5. Deploys the container app with your API key
# =============================================================================

set -euo pipefail

# --- Configuration (edit these) -----------------------------------------------
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rag-chatbot-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
ACR_NAME="${AZURE_ACR_NAME:-ragchatbotacr}"
APP_NAME="${AZURE_APP_NAME:-rag-chatbot}"
ENVIRONMENT_NAME="${AZURE_ENV_NAME:-rag-chatbot-env}"
IMAGE_TAG="latest"
# ------------------------------------------------------------------------------

echo "=== Agentic RAG System — Azure Container Apps Deployment ==="
echo ""
echo "Resource Group : $RESOURCE_GROUP"
echo "Location       : $LOCATION"
echo "ACR Name       : $ACR_NAME"
echo "App Name       : $APP_NAME"
echo ""

# Validate API key
if [ -z "${GOOGLE_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: Set GOOGLE_API_KEY or OPENAI_API_KEY before running this script."
    echo "  export GOOGLE_API_KEY='your-key'"
    exit 1
fi

# Step 1: Create resource group
echo "→ Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Step 2: Create container registry
echo "→ Creating Azure Container Registry..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none

# Step 3: Build and push Docker image
echo "→ Building and pushing Docker image to ACR..."
az acr build \
    --registry "$ACR_NAME" \
    --image "${APP_NAME}:${IMAGE_TAG}" \
    --file Dockerfile \
    .

# Step 4: Create Container Apps environment
echo "→ Creating Container Apps environment..."
az containerapp env create \
    --name "$ENVIRONMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# Step 5: Get ACR credentials
ACR_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

# Step 6: Deploy container app
echo "→ Deploying container app..."
ENV_VARS_ARGS=(STREAMLIT_SERVER_PORT=8501)
if [ -n "${GOOGLE_API_KEY:-}" ]; then
    ENV_VARS_ARGS+=("GOOGLE_API_KEY=${GOOGLE_API_KEY}")
fi
if [ -n "${OPENAI_API_KEY:-}" ]; then
    ENV_VARS_ARGS+=("OPENAI_API_KEY=${OPENAI_API_KEY}")
fi

az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT_NAME" \
    --image "${ACR_SERVER}/${APP_NAME}:${IMAGE_TAG}" \
    --registry-server "$ACR_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 8501 \
    --ingress external \
    --cpu 1.0 \
    --memory 2.0Gi \
    --min-replicas 0 \
    --max-replicas 3 \
    --env-vars "${ENV_VARS_ARGS[@]}" \
    --output none

# Step 7: Get the app URL
APP_URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv)

echo ""
echo "=== Deployment complete! ==="
echo ""
echo "  Streamlit UI : https://${APP_URL}"
echo "  API (internal): port 8000 (accessible from within the container)"
echo ""
echo "To tear down:"
echo "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
