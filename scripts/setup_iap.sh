#!/bin/bash
# Setup Identity-Aware Proxy (IAP) for Cloud Run
# Usage: ./scripts/setup_iap.sh <DOMAIN_NAME> <IAP_CLIENT_ID> <IAP_CLIENT_SECRET>

set -e

# Configuration
PROJECT_ID="looker-private-demo"
SERVICE_NAME="gaming-analytics"
REGION="us-central1"
IAP_BACKEND_SERVICE="gaming-analytics-backend"
URL_MAP_NAME="gaming-analytics-url-map"
SSL_CERT_NAME="gaming-analytics-cert"
IP_NAME="gaming-analytics-ip"

# Inputs
DOMAIN_NAME="$1"
IAP_CLIENT_ID="$2"
IAP_CLIENT_SECRET="$3"

if [ -z "$DOMAIN_NAME" ] || [ -z "$IAP_CLIENT_ID" ] || [ -z "$IAP_CLIENT_SECRET" ]; then
  echo "Usage: $0 <DOMAIN_NAME> <IAP_CLIENT_ID> <IAP_CLIENT_SECRET>"
  echo "Example: $0 analytics.example.com client-id-123 client-secret-456"
  exit 1
fi

echo "=== Setting up IAP for $DOMAIN_NAME ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# 1. Reserve Static Global IP
echo "1. Reserving Static IP..."
if gcloud compute addresses describe $IP_NAME --global --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  IP $IP_NAME already exists."
else
  gcloud compute addresses create $IP_NAME --global --project $PROJECT_ID
fi
IP_ADDRESS=$(gcloud compute addresses describe $IP_NAME --global --project $PROJECT_ID --format='value(address)')
echo "  IP Address: $IP_ADDRESS"
echo "  -> ACTION REQUIRED: Point your DNS A record for $DOMAIN_NAME to $IP_ADDRESS"

# 2. Create Network Endpoint Group (NEG)
echo "2. Creating Serverless NEG..."
if gcloud compute network-endpoint-groups describe $SERVICE_NAME-neg --region $REGION --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  NEG already exists."
else
  gcloud compute network-endpoint-groups create $SERVICE_NAME-neg \
    --region=$REGION \
    --network-endpoint-type=serverless \
    --cloud-run-service=$SERVICE_NAME \
    --project=$PROJECT_ID
fi

# 3. Create Backend Service with IAP
# 3. Create Backend Service with IAP
echo "3. Creating Backend Service..."
if gcloud compute backend-services describe $IAP_BACKEND_SERVICE --global --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  Backend service exists. Updating IAP settings..."
  gcloud compute backend-services update $IAP_BACKEND_SERVICE \
    --global --project $PROJECT_ID \
    --iap=enabled,oauth2-client-id=$IAP_CLIENT_ID,oauth2-client-secret=$IAP_CLIENT_SECRET
else
  # Use HTTP for Serverless NEGs to avoid portName issues
  gcloud compute backend-services create $IAP_BACKEND_SERVICE \
    --global --protocol=HTTP --project $PROJECT_ID \
    --iap=enabled,oauth2-client-id=$IAP_CLIENT_ID,oauth2-client-secret=$IAP_CLIENT_SECRET
fi

# Add NEG to Backend Service if not already present
if gcloud compute backend-services describe $IAP_BACKEND_SERVICE --global --project $PROJECT_ID | grep -q "$SERVICE_NAME-neg"; then
  echo "  NEG already added to backend service."
else
  echo "  Adding NEG to backend service..."
  gcloud compute backend-services add-backend $IAP_BACKEND_SERVICE \
    --global --project $PROJECT_ID \
    --network-endpoint-group=$SERVICE_NAME-neg \
    --network-endpoint-group-region=$REGION
fi

# 4. create Managed SSL Certificate
echo "4. Creating Managed SSL Certificate..."
if gcloud compute ssl-certificates describe $SSL_CERT_NAME --global --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  Certificate $SSL_CERT_NAME already exists."
else
  gcloud compute ssl-certificates create $SSL_CERT_NAME \
    --domains=$DOMAIN_NAME \
    --global --project $PROJECT_ID
fi

# 5. Create URL Map
echo "5. Creating URL Map..."
if gcloud compute url-maps describe $URL_MAP_NAME --global --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  URL Map exists."
else
  gcloud compute url-maps create $URL_MAP_NAME \
    --default-service=$IAP_BACKEND_SERVICE \
    --global --project $PROJECT_ID
fi

# 6. Create Target HTTPS Proxy
echo "6. Creating Target HTTPS Proxy..."
if gcloud compute target-https-proxies describe $SERVICE_NAME-https-proxy --global --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  Target Proxy exists."
else
  gcloud compute target-https-proxies create $SERVICE_NAME-https-proxy \
    --ssl-certificates=$SSL_CERT_NAME \
    --url-map=$URL_MAP_NAME \
    --global --project $PROJECT_ID
fi

# 7. Create Global Forwarding Rule
echo "7. Creating Forwarding Rule..."
if gcloud compute forwarding-rules describe $SERVICE_NAME-lb-forwarding-rule --global --project $PROJECT_ID > /dev/null 2>&1; then
  echo "  Forwarding Rule exists."
else
  gcloud compute forwarding-rules create $SERVICE_NAME-lb-forwarding-rule \
    --load-balancing-scheme=EXTERNAL \
    --network-tier=PREMIUM \
    --address=$IP_NAME \
    --target-https-proxy=$SERVICE_NAME-https-proxy \
    --global \
    --ports=443 \
    --project $PROJECT_ID
fi

# 8. Grant IAP Access
echo "8. Granting IAP Access to domain:google.com..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="domain:google.com" \
    --role="roles/iap.httpsResourceAccessor" > /dev/null

echo ""
echo "=== IAP Setup Complete ==="
echo "1. DNS: Ensure $DOMAIN_NAME points to $IP_ADDRESS"
echo "2. SSL: Wait for Google to provision the certificate (15-60m)."
echo "3. OAuth: Add 'https://$DOMAIN_NAME/login/callback' to your OAuth Client authorized redirect URIs."
