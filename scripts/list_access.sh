#!/bin/bash
# List all users with access to the Gaming Analytics Cloud Run service
# Usage: ./scripts/list_access.sh

set -e

SERVICE_NAME="gaming-analytics"
REGION="us-central1"

# Load project ID from .env if available
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: PROJECT_ID not set. Please set it in .env or export it."
  exit 1
fi

echo "=== Users with access to $SERVICE_NAME ==="
echo ""

gcloud run services get-iam-policy $SERVICE_NAME \
  --project $PROJECT_ID \
  --region $REGION \
  --format="table(bindings.role,bindings.members)"
