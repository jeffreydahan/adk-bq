#!/bin/bash

# --- Variables ---
PROJECT_ID=$(gcloud config get-value project)
DISCOVERY_ENGINE_API_BASE_URL="https://discoveryengine.googleapis.com/v1alpha"

# --- Script Body ---
AUTH_TOKEN=$(gcloud auth print-access-token)

echo "Listing authorizations for project: ${PROJECT_ID}"
curl -X GET \
     -H "Authorization: Bearer ${AUTH_TOKEN}" \
     -H "Content-Type: application/json" \
     -H "X-Goog-User-Project: ${PROJECT_ID}" \
     "${DISCOVERY_ENGINE_API_BASE_URL}/projects/${PROJECT_ID}/locations/global/authorizations"
