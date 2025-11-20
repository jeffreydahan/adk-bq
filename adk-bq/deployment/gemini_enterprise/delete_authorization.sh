#!/bin/bash

# --- Variables ---
# Source .env file from project root relative to the script location
if [ -f "$(dirname "$0")/../../.env" ]; then
    source "$(dirname "$0")/../../.env"
fi

PROJECT_ID=$(gcloud config get-value project)
AUTHORIZATION_ID=$BQ_AUTHORIZATION_ID
DISCOVERY_ENGINE_API_BASE_URL="https://discoveryengine.googleapis.com/v1alpha"

# --- Script Body ---
AUTH_TOKEN=$(gcloud auth print-access-token)

curl -X DELETE \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${DISCOVERY_ENGINE_API_BASE_URL}/projects/${PROJECT_ID}/locations/global/authorizations/${AUTHORIZATION_ID}"