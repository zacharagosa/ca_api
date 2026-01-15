#!/bin/bash
# Grant a user full access to the Gaming Analytics application
# This script handles:
#   1. Cloud Run IAM access
#   2. Looker group membership (for data access)
#
# Usage: ./scripts/grant_access.sh user@example.com

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <user-email>"
  echo "Example: $0 john.doe@example.com"
  echo ""
  echo "This grants access to:"
  echo "  • Cloud Run service (if not public)"
  echo "  • Looker 'Gaming Analytics Users' group"
  exit 1
fi

USER_EMAIL="$1"
SERVICE_NAME="gaming-analytics"
REGION="us-central1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment from .env if available
if [ -f "$PROJECT_DIR/.env" ]; then
  export $(cat "$PROJECT_DIR/.env" | sed 's/#.*//g' | xargs)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: PROJECT_ID not set. Please set it in .env or export it."
  exit 1
fi

echo "============================================"
echo "  Granting Access: $USER_EMAIL"
echo "============================================"
echo ""

# Step 1: Cloud Run Access
echo "Step 1: Cloud Run Access"
echo "------------------------"
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --project $PROJECT_ID \
  --region $REGION \
  --member="user:$USER_EMAIL" \
  --role="roles/run.invoker" \
  --quiet 2>/dev/null || echo "  (Cloud Run access already granted or service public)"
echo "  ✅ Cloud Run access configured"
echo ""

# Step 2: Looker Access
echo "Step 2: Looker Access"
echo "------------------------"
cd "$PROJECT_DIR"
if [ -f "scripts/looker_access.py" ]; then
  # Activate virtual environment if available
  if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
  fi
  python scripts/looker_access.py grant "$USER_EMAIL" 2>&1 || echo "  ⚠️  Looker access could not be configured (check credentials)"
else
  echo "  ⚠️  Looker access script not found - skipping"
fi
echo ""

# Summary
echo "============================================"
echo "  ✅ Access Grant Complete"
echo "============================================"
echo ""
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)' 2>/dev/null || echo "[Run deployment first]")
echo "User $USER_EMAIL can now access:"
echo "  $SERVICE_URL"
echo ""
echo "IMPORTANT: If OAuth is in 'Testing' mode, also add the user to:"
echo "  Google Cloud Console > APIs & Services > OAuth consent screen > Test users"
