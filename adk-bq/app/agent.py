# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.apps.app import App

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys, re, json
import logging
import google.cloud.logging

from typing import Any, Dict, Optional
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.genai import types
from dotenv import load_dotenv
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset
from google.adk.tools.apihub_tool.clients.secret_client import SecretManagerClient
from google.adk.auth import AuthCredential, AuthCredentialTypes, OAuth2Auth
from google.adk.auth.auth_credential import HttpAuth, HttpCredentials
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.oauth2.credentials import Credentials
from google.adk.tools.base_tool import BaseTool

import google.auth
import google.auth.transport.requests

from fastapi.openapi.models import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows

from .prompts import root_agent_instructions, cloud_bqoauth_agent_instructions
from .tools import app_int_cloud_bqoauth_connector


load_dotenv()

IS_RUNNING_IN_GCP = os.getenv("K_SERVICE") is not None

# Check if running in a GCP environment
if IS_RUNNING_IN_GCP:
    # Set up Google Cloud Logging
    client = google.cloud.logging.Client()
    client.setup_logging()
    logging.basicConfig(level=logging.INFO)
    logging.info("Running in GCP. Configured Google Cloud Logging.")
else:
    # Set up basic logging for local development
    logging.basicConfig(level=logging.INFO)
    logging.info("Running locally. Using basic console logging.")

logger = logging.getLogger(__name__)


logger.info("Libraries imported.")

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

auth_id=os.getenv("BQ_AUTHORIZATION_ID") 
dynamic_auth_param_name = "dynamic_auth_config" # Name of the parameter to inject
dynamic_auth_internal_key = "oauth2_auth_code_flow.access_token" # Internal key for the token

def get_local_dev_token() -> str:
    """Function which checks if the agent is running locally via ADK web and if so,
    obtains an access token using google-auth library and stores it in the 
    tool context state.
    
    If running in the cloud, the env variable K_SERVICE will be set, and the function
    will return without taking any action, as the token is handled automatically.
    
    If running locally, the K_SERVICE env variable will not be set, and the function 
    will attempt to get the token and store it in the tool context state under the 
    auth_id key.
    """
    # If not running in a deployed Cloud Run environment (e.g., running locally)
    if not IS_RUNNING_IN_GCP:
        try:
            credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            logger.info("Running locally in ADK, obtained token using google-auth.")
            token_key = credentials.token
            
        except Exception as e:
            logger.error(f"Could not get access token using google-auth: {e}")
            # Fallback to trying to find the token in the state, in case it was set by other means
            pass
    else:
        logger.info(f"Running on Agent Engine or Gemini Enterprise. OAUTH handled automatically.  Confirmed by finding environment variable K_SERVICE={os.getenv('K_SERVICE')}")
        token_key = None
    
    return token_key


def dynamic_token_injection(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    # Call function to get local dev token if agent is running via adk web (locally)
    token_key = None
    # get local token key if running locally
    token_key = get_local_dev_token()
    
    if token_key:
        # running locally and obtained token
        tool_context.state['temp:'+auth_id+'_0'] = token_key
    
    pattern = re.compile(r'.*'+auth_id+'.*')
    # logger.info("Checking for pattern using regex: %s", pattern.pattern)

    state_dict = tool_context.state.to_dict()
    # logger.info("Current tool context state keys: %s", state_dict)
    matched_auth = {key: value for key, value in state_dict.items() if pattern.match(key)}
    if len(matched_auth) > 0:
        token_key = list(matched_auth.keys())[0]
    else:
        logger.warning("No valid tokens found")
        return None
        
    access_token = state_dict[token_key]
    dynamic_auth_config = {dynamic_auth_internal_key: access_token}
    args[dynamic_auth_param_name] = json.dumps(dynamic_auth_config)
    return None

# Define the bqoauth Agent with tools and instructions
cloud_bqoauth_agent = Agent(
    model="gemini-2.5-flash",
    name="cloud_bqoauth_agent",
    instruction=cloud_bqoauth_agent_instructions,
    tools=[app_int_cloud_bqoauth_connector],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
    before_tool_callback=dynamic_token_injection
)

# Define the root agent with tools and instructions
root_agent = Agent(
    model="gemini-2.5-flash",
    name="RootAgent",
    instruction=root_agent_instructions,
    tools=[AgentTool(agent=cloud_bqoauth_agent)],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)

app = App(root_agent=root_agent, name="app")
