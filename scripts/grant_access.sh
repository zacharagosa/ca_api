#!/bin/bash
# Grant a user access to the Gaming Analytics Cloud Run service
# Usage: ./scripts/grant_access.sh user@example.com

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

echo "Granting access to: $USER_EMAIL"
echo "Service: $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo ""

# Grant Cloud Run Invoker role
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --project $PROJECT_ID \
  --region $REGION \
  --member="user:$USER_EMAIL" \
  --role="roles/run.invoker"

echo ""
echo "✅ Access granted!"
echo ""
echo "The user can now access the application at:"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)' 2>/dev/null || echo "[Run deployment first]")
echo "  $SERVICE_URL"
echo ""
echo "They should sign into Chrome with their Google account ($USER_EMAIL)"
echo "and navigate to the URL above."
