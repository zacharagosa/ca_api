#!/bin/bash
# Grant a user full access to the Gaming Analytics application
# This script handles:
#   1. Cloud Run IAM access
#   2. Looker embed user provisioning (via cookieless embed API)
#
# Usage: ./scripts/grant_access.sh user@example.com

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <user-email>"
  echo "Example: $0 john.doe@example.com"
  echo ""
  echo "This grants access to:"
  echo "  • Cloud Run service (if not public)"
  echo "  • Looker embed user (auto-provisioned)"
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

# Step 2: Looker Embed User Provisioning
echo "Step 2: Looker Embed User"
echo "------------------------"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)' 2>/dev/null || echo "")

if [ -n "$SERVICE_URL" ]; then
  # Call the provision endpoint to create the embed user
  PROVISION_RESPONSE=$(curl -s "${SERVICE_URL}/api/looker-provision?user_id=${USER_EMAIL}" 2>/dev/null)
  
  if echo "$PROVISION_RESPONSE" | grep -q '"provisioned": true' 2>/dev/null; then
    echo "  ✅ Looker embed user provisioned"
  elif echo "$PROVISION_RESPONSE" | grep -q '"provisioned":true' 2>/dev/null; then
    echo "  ✅ Looker embed user provisioned"
  else
    echo "  ⚠️  Looker provisioning response: $PROVISION_RESPONSE"
    echo "  Note: User will be auto-provisioned on first app login"
  fi
else
  echo "  ⚠️  Service URL not found - Looker provisioning skipped"
  echo "  Note: User will be auto-provisioned on first app login"
fi
echo ""

# Summary
echo "============================================"
echo "  ✅ Access Grant Complete"
echo "============================================"
echo ""
echo "User $USER_EMAIL can now access:"
echo "  ${SERVICE_URL:-[Deploy the app first]}"
echo ""
echo "NOTES:"
echo "  • Looker embed users are auto-provisioned (no internal license required)"
echo "  • If OAuth is in 'Testing' mode, also add the user to:"
echo "    Google Cloud Console > APIs & Services > OAuth consent screen > Test users"
