#!/bin/bash
source .env

# Get GCP Access Token
ACCESS_TOKEN=$(gcloud auth print-access-token)

# Use the following from the .env file, or a default if not set
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
COLLECTION_ID=$GEM_ENT_COLLECTION_ID
ENGINE_ID=$GEM_ENT_ENGINE_ID
ASSISTANT_ID=$GEM_ENT_ASSISTANT_ID
# Get the REASONING_ENGINE_ID from deployment_metadata.json
REASONING_ENGINE_ID=$(jq -r '.remote_agent_engine_id' deployment_metadata.json)
AGENT_NAME=$ADK_AGENT_NAME
AGENT_DESCRIPTION=$ADK_AGENT_DESCRIPTION
TOOL_DESCRIPTION=$ADK_AGENT_TOOL_DESCRIPTION
AGENT_ICON_URI=$ADK_AGENT_ICON_URI
AUTH_ID=$BQ_AUTHORIZATION_ID

# Get the Project Number from the Project ID
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='get(projectNumber)')
echo "PROJECT_NUMBER: ${PROJECT_NUMBER}"

# Build the service account principal using the Project Number service-[ProjectNumber]@gcp-sa-aiplatform-re.iam.gserviceaccount.com
# SERVICE_ACCOUNT_PRINCIPAL="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
# Grand the role of Application Integration Invoker to the service account principal
# gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
#     --member="serviceAccount:${SERVICE_ACCOUNT_PRINCIPAL}" \
#     --role="roles/integrations.integrationInvoker"

# Build API Endpoint - it must use the 'global' location hard coded
API_ENDPOINT="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/${COLLECTION_ID}/engines/${ENGINE_ID}/assistants/${ASSISTANT_ID}/agents"

# Build the JSON payload using a heredoc for better readability and safety
read -r -d '' JSON_PAYLOAD <<EOF
{
    "displayName": "${AGENT_NAME}",
    "description": "${AGENT_DESCRIPTION}",
    "adkAgentDefinition": {
        "toolSettings": {
            "toolDescription": "${TOOL_DESCRIPTION}"
        },
        "provisionedReasoningEngine": {
            "reasoningEngine": "${REASONING_ENGINE_ID}"
        },
        "authorizations": [
            "projects/${PROJECT_NUMBER}/locations/global/authorizations/${AUTH_ID}"
        ]
    }
}
EOF

# If AGENT_ICON_URI is set and not "NONE", add the icon object to the payload
if [ -n "${AGENT_ICON_URI}" ] && [ "${AGENT_ICON_URI}" != "NONE" ]; then
    # Use jq to safely add the icon object to the JSON
    JSON_PAYLOAD=$(echo "${JSON_PAYLOAD}" | jq --arg uri "${AGENT_ICON_URI}" '. + {icon: {uri: $uri}}')
fi

echo "---"
echo "Using the following JSON payload:"
echo "${JSON_PAYLOAD}"
echo "---"

# Execute
curl -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Goog-User-Project: ${PROJECT_ID}" \
    "${API_ENDPOINT}" \
    -d "${JSON_PAYLOAD}"

# Go to Agentspace and click Agents to view and test your agent.
# If you want to delete the Agent, just click the 3 dots on the Agent
# and select Delete.