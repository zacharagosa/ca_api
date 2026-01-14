#!/bin/bash
# Revoke a user's access to the Gaming Analytics Cloud Run service
# Usage: ./scripts/revoke_access.sh user@example.com

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <user-email>"
  echo "Example: $0 john.doe@example.com"
  exit 1
fi

USER_EMAIL="$1"
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

echo "Revoking access for: $USER_EMAIL"
echo "Service: $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo ""

# Remove Cloud Run Invoker role
gcloud run services remove-iam-policy-binding $SERVICE_NAME \
  --project $PROJECT_ID \
  --region $REGION \
  --member="user:$USER_EMAIL" \
  --role="roles/run.invoker"

echo ""
echo "✅ Access revoked for $USER_EMAIL"
