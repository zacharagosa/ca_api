#!/bin/bash
# Deploy Gaming Analytics to 'looker-private-demo' with IAP for @google.com access
# Uses the new Cloud Run IAP preview feature (no load balancer required)
set -e

# Load secrets from .env if present (we still need client secrets etc)
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Override PROJECT_ID to ensure we deploy to the correct project
PROJECT_ID="looker-private-demo"
SERVICE_NAME="gaming-analytics"
REGION="us-central1"

echo "=== Deployment to $PROJECT_ID with IAP ==="
echo "Using Cloud Run IAP preview to restrict access to @google.com domain."
echo ""

# Get project number (needed for IAP service agent)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
echo "Project Number: $PROJECT_NUMBER"

# Step 0: Enable required APIs
echo "0. Enabling required APIs..."
gcloud services enable iap.googleapis.com --project $PROJECT_ID

# Step 1: Build frontend
echo "1. Building frontend..."
if [ -d "frontend" ]; then
    cd frontend
    npm run build
    cd ..
else
    echo "Frontend directory not found!"
    exit 1
fi

# Step 2: Deploy to Cloud Run (Load balancer handles IAP)
# NOTE: Do NOT use --iap flag here - IAP is configured on the load balancer
echo "2. Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --project ${PROJECT_ID} \
  --source . \
  --region $REGION \
  --no-allow-unauthenticated \
  --ingress all \
  --cpu 2 \
  --memory 2Gi \
  --min-instances 1 \
  --max-instances 10 \
  --concurrency 20 \
  --set-env-vars PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION:-global},LOOKER_CLIENT_ID=${LOOKER_CLIENT_ID},LOOKER_CLIENT_SECRET=${LOOKER_CLIENT_SECRET},LOOKER_INSTANCE_URI=${LOOKER_INSTANCE_URI},LOOKML_MODEL=${LOOKML_MODEL:-gaming},EXPLORE=${EXPLORE:-events},DATASET_NAME=${DATASET_NAME:-googledemo},LOOKER_CLIENT_ID_GOOGLEDEMO=${LOOKER_CLIENT_ID_GOOGLEDEMO},LOOKER_CLIENT_SECRET_GOOGLEDEMO=${LOOKER_CLIENT_SECRET_GOOGLEDEMO}

# Step 3: Grant IAP service agent permission to invoke Cloud Run
echo "3. Granting IAP service agent invoker access..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --project $PROJECT_ID \
  --region $REGION \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Step 4: Grant @google.com domain access via IAP policy
echo "4. Granting IAP access to domain:google.com..."
gcloud beta iap web add-iam-policy-binding \
  --project $PROJECT_ID \
  --member="domain:google.com" \
  --role="roles/iap.httpsResourceAccessor" \
  --region=$REGION \
  --resource-type=cloud-run \
  --service=$SERVICE_NAME

# Verify IAP is enabled
echo ""
echo "5. Verifying IAP configuration..."
gcloud beta run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID | grep -i "iap"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Access is restricted to users with @google.com accounts via IAP."
echo "Users will see a Google login page when accessing the URL."
