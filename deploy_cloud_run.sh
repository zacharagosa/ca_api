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

# Validate required environment variables
if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: PROJECT_ID not set. Please set it in .env or export it."
  exit 1
fi

echo "=== Gaming Analytics Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Step 1: Build frontend
echo "1. Building frontend..."
cd frontend
npm run build
cd ..

# Step 2: Deploy to Cloud Run (IAM-protected)
echo "2. Deploying to Cloud Run (IAM-protected)..."
gcloud run deploy $SERVICE_NAME \
  --project ${PROJECT_ID} \
  --source . \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION:-global},LOOKER_CLIENT_ID=${LOOKER_CLIENT_ID},LOOKER_CLIENT_SECRET=${LOOKER_CLIENT_SECRET},LOOKER_INSTANCE_URI=${LOOKER_INSTANCE_URI},LOOKML_MODEL=${LOOKML_MODEL:-gaming},EXPLORE=${EXPLORE:-events},DATASET_NAME=${DATASET_NAME:-events}

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)')

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
