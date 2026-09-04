#!/bin/bash
# ==============================================================================
# Publish Gaming Analytics Agent to Gemini Enterprise (GE)
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

# Load environment
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
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"gaming-analytics"}

echo "=================================================================="
echo "  🚀 Publishing Gaming Analytics Agent to Gemini Enterprise (GE)"
echo "  GCP Project ID: $GCP_PROJECT (Number: $PROJECT_NUM) | Region: $REGION"
echo "=================================================================="

# 1. Verify OpenAPI spec
if [ ! -f "gemini_enterprise_openapi.yaml" ]; then
  echo "❌ Error: gemini_enterprise_openapi.yaml not found."
  exit 1
fi

# 2. Deploy/Sync to Cloud Run
echo ""
echo "1. Building frontend & deploying backend to Cloud Run..."
cd frontend
npm run build
cd ..

gcloud run deploy $SERVICE_NAME \
  --project ${GCP_PROJECT} \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=${PROJECT_NUM},GCP_PROJECT_ID=${GCP_PROJECT},LOCATION=${LOCATION:-global},LOOKER_CLIENT_ID=${LOOKER_CLIENT_ID},LOOKER_CLIENT_SECRET=${LOOKER_CLIENT_SECRET},LOOKER_INSTANCE_URI=${LOOKER_INSTANCE_URI},LOOKML_MODEL=${LOOKML_MODEL:-gaming},EXPLORE=${EXPLORE:-events},DATASET_NAME=${DATASET_NAME:-events},NARRATIVE_SECRET_TOKEN=${NARRATIVE_SECRET_TOKEN}

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $GCP_PROJECT --format='value(status.url)')

echo ""
echo "=================================================================="
echo "  ✨ Cloud Run Backend Deployed: $SERVICE_URL"
echo "  OpenAPI Spec URL: $SERVICE_URL/openapi.yaml"
echo "=================================================================="
echo ""
echo "2. Publishing Options for Gemini Enterprise:"
echo ""
echo "------------------------------------------------------------------"
echo "OPTION A: Gemini Enterprise Agent Designer (Recommended for Demos)"
echo "------------------------------------------------------------------"
echo "1. Navigate to Gemini Enterprise: go/ge (or console.cloud.google.com/gemini-enterprise)"
echo "2. Click 'Agents' in the left navigation sidebar -> 'Create Agent'."
echo "3. Agent Details:"
echo "   - Name: Gaming Analytics AI"
echo "   - Description: Enterprise autonomous agent for Looker metrics, Spanner graph clan rosters, and LiveOps dashboards."
echo "4. Under 'Instructions': Copy content from 'gemini_enterprise_instructions.md'."
echo "5. Under 'Tools / Actions':"
echo "   - Click 'Add Tool' -> 'OpenAPI'."
echo "   - Tool Name: GamingAnalyticsAPI"
echo "   - Import via URL: $SERVICE_URL/openapi.yaml (or upload gemini_enterprise_openapi.yaml)"
echo "6. Test in the Preview window with: 'What was our total revenue and DAU yesterday?'"
echo "7. Click 'Publish' / 'Share with Organization'."
echo ""
echo "------------------------------------------------------------------"
echo "OPTION B: Vertex AI Agent Registry (High-Code ADK Import)"
echo "------------------------------------------------------------------"
echo "1. Run the Reasoning Engine deployment script:"
echo "   python deploy_gemini_enterprise_agent.py"
echo "2. In Gemini Enterprise, go to 'Agent Management' -> 'Import from Agent Registry'."
echo "3. Select 'Gaming Analytics Intelligence' and grant user/group IAM access."
echo ""
echo "=================================================================="
echo "  Both the Web App ($SERVICE_URL) and the Gemini Enterprise agent "
echo "  are now active and can be demonstrated concurrently!            "
echo "=================================================================="
