#!/bin/bash
# Deploy Gaming Analytics to Cloud Run with IAM authentication
set -e

# Configuration
SERVICE_NAME="gaming-analytics"
REGION="us-central1"

# Load secrets from .env if present
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Determine alphanumeric Project ID for gcloud commands vs numeric Project Number for Vertex AI
GCP_PROJECT="${GCP_PROJECT_ID:-$PROJECT_ID}"
if [[ "$GCP_PROJECT" =~ ^[0-9]+$ ]]; then
  if [ -n "$GCP_PROJECT_ID" ] && ! [[ "$GCP_PROJECT_ID" =~ ^[0-9]+$ ]]; then
    GCP_PROJECT="$GCP_PROJECT_ID"
  else
    GCP_PROJECT="aragosalooker"
  fi
fi

PROJECT_NUM=${PROJECT_ID:-"1094200614711"}

echo "=== Gaming Analytics Deployment ==="
echo "Project ID: $GCP_PROJECT (Number: $PROJECT_NUM)"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Step 1: Build frontend
echo "1. Building frontend..."
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    \. "$NVM_DIR/nvm.sh"
fi
cd frontend
npm run build
cd ..

# Step 2: Deploy to Cloud Run (IAM-protected)
echo "2. Deploying to Cloud Run (IAM-protected)..."
gcloud run deploy $SERVICE_NAME \
  --project ${GCP_PROJECT} \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=${PROJECT_NUM},GCP_PROJECT_ID=${GCP_PROJECT},LOCATION=${LOCATION:-global},DEFAULT_MODEL=${DEFAULT_MODEL:-gemini-3.8-flash},DEEP_MODE_MODEL=${DEEP_MODE_MODEL:-gemini-3.8-flash},LOOKER_CLIENT_ID=${LOOKER_CLIENT_ID},LOOKER_CLIENT_SECRET=${LOOKER_CLIENT_SECRET},LOOKER_INSTANCE_URI=${LOOKER_INSTANCE_URI},LOOKML_MODEL=${LOOKML_MODEL:-gaming},EXPLORE=${EXPLORE:-events},DATASET_NAME=${DATASET_NAME:-events},NARRATIVE_SECRET_TOKEN=${NARRATIVE_SECRET_TOKEN}

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $GCP_PROJECT --format='value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: $SERVICE_URL"
echo ""
echo "IMPORTANT: This service requires IAM authentication."
echo "To grant a user access, run:"
echo "  ./scripts/grant_access.sh user@example.com"
echo ""
echo "Users can access the app by visiting the URL in a browser"
echo "while signed into their authorized Google account."
