#!/bin/bash

# --- Variables ---
# Source .env file from project root relative to the script location
if [ -f "$(dirname "$0")/../../.env" ]; then
    source "$(dirname "$0")/../../.env"
fi

PROJECT_ID=$(gcloud config get-value project)
AUTHORIZATION_ID=$BQ_AUTHORIZATION_ID
CLIENT_ID=$(gcloud secrets versions access latest --secret "${BQ_SECMGR_ID}" --project "${PROJECT_ID}") # The OAuth 2.0 Client ID from your Google Cloud project
CLIENT_SECRET=$(gcloud secrets versions access latest --secret "${BQ_SECMGR_SECRET}" --project "${PROJECT_ID}") # The OAuth 2.0 Client Secret from your Google Cloud project
SCOPES=$BQ_OAUTH_SCOPES
DISCOVERY_ENGINE_API_BASE_URL="https://discoveryengine.googleapis.com/v1alpha"

# --- Script Body ---
AUTH_TOKEN=$(gcloud auth print-access-token)

# Construct the authorizationUri separately and URL-encode the scopes
# Using printf %s to avoid issues with newline in variable expansion
ENCODED_SCOPES=$(printf %s "${SCOPES}" | sed 's/ /+/g') # More robust way to replace spaces with +

AUTHORIZATION_URI="https://accounts.google.com/o/oauth2/v2/auth?&scope=${ENCODED_SCOPES}&include_granted_scopes=true&response_type=code&access_type=offline&prompt=consent"

# Create the JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
  "name": "projects/${PROJECT_ID}/locations/global/authorizations/${AUTHORIZATION_ID}",
  "serverSideOauth2": {
    "clientId": "${CLIENT_ID}",
    "clientSecret": "${CLIENT_SECRET}",
    "authorizationUri": "${AUTHORIZATION_URI}",
    "tokenUri": "https://oauth2.googleapis.com/token"
  }
}
EOF
)

curl -X POST \
     -H "Authorization: Bearer ${AUTH_TOKEN}" \
     -H "Content-Type: application/json" \
     -H "X-Goog-User-Project: ${PROJECT_ID}" \
     "${DISCOVERY_ENGINE_API_BASE_URL}/projects/${PROJECT_ID}/locations/global/authorizations?authorizationId=${AUTHORIZATION_ID}" \
     -d "${JSON_PAYLOAD}"