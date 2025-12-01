#!/bin/bash
set -e

echo "Building frontend..."
cd frontend
npm run build
cd ..

echo "Deploying to Cloud Run..."
gcloud run deploy ca-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=aragosalooker,LOCATION=us-central1

echo "Deployment complete!"
