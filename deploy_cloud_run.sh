#!/bin/bash
set -e

# Load secrets from .env if present
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

echo "Building frontend..."
cd frontend
npm run build
cd ..

echo "Deploying to Cloud Run..."
gcloud run deploy ca-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION},LOOKER_CLIENT_ID=${LOOKER_CLIENT_ID},LOOKER_CLIENT_SECRET=${LOOKER_CLIENT_SECRET},LOOKER_INSTANCE_URI=${LOOKER_INSTANCE_URI}

echo "Deployment complete!"
