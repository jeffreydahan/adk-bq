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

"""This file defines the core agent logic for the BigQuery agent."""

import os
import sys, re, json
import logging
import google.cloud.logging

from typing import Any, Dict, Optional
from google.adk.apps.app import App
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.genai import types
from dotenv import load_dotenv
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset
from google.adk.tools.apihub_tool.clients.secret_client import SecretManagerClient
from google.adk.tools.base_tool import BaseTool

import google.auth
import google.auth.transport.requests

from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext 
from google.adk.models import LlmResponse

from .prompts import root_agent_instructions, cloud_bqoauth_agent_instructions
from .tools import app_int_cloud_bqoauth_connector


load_dotenv()

# This flag checks for the K_SERVICE environment variable, which is set in
# Google Cloud Run and other serverless environments. It allows the agent to
# dynamically change its behavior based on whether it's running locally or deployed.
IS_RUNNING_IN_GCP = os.getenv("K_SERVICE") is not None

# This block configures the logging.
# If the agent is running in a GCP environment, it sets up the
# Google Cloud Logging client to send logs in a structured format
# that can be easily viewed and filtered in the GCP Log Explorer.
# Otherwise, it falls back to a basic console logger for local development.
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

LATEST_ACCESS_TOKEN: Optional[str] = None

def get_local_dev_token() -> str:
    """Handles authentication when running the agent locally.

    When an agent is deployed to a managed environment like Gemini Enterprise or
    Agent Engine on Cloud Run, the platform automatically handles OAuth and
    places the necessary access tokens into the agent's session state.

    However, when running locally using `adk web`, this process doesn't happen.
    This function bridges that gap. It uses the developer's local `gcloud`
    credentials to generate an access token, mimicking the behavior of the
    deployed environment. This allows the same tool authentication logic to work
    seamlessly in both local and deployed settings.

    Returns:
        The access token if running locally, otherwise None.
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
    """Injects an OAuth token into the tool arguments before execution.

    This function is registered as a `before_tool_callback` on the agent. It
    intercepts any tool call and performs the following steps:

    1.  If running locally, it calls `get_local_dev_token()` to obtain a token
        and adds it to the session state.
    2.  It searches the session state for a valid OAuth token. In a deployed
        environment, Gemini Enterprise/Agent Engine places this token in the
        state automatically.
    3.  If a token is found, it is packaged into a JSON structure that the
        Application Integration tool expects.
    4.  This JSON structure is then injected into the tool's arguments under
        the `dynamic_auth_config` parameter, allowing the tool to authenticate
        its call to the backend service.

    Args:
        tool: The tool being called.
        args: The arguments for the tool.
        tool_context: The context for the tool call, including session state.

    Returns:
        None. The function modifies the `args` dictionary in place.
    """
    # Call function to get local dev token if agent is running via adk web (locally)
    # token_key = None
    # get local token key if running locally
    
    # check if the token is already in state

    # Use global scope for the token variable
    global LATEST_ACCESS_TOKEN

    token_state_key = 'temp:'+auth_id+'_0'
    token_key = tool_context.state.get(token_state_key, None)

    if token_key is None and LATEST_ACCESS_TOKEN is not None:
        logger.info("Token not in tool_context.state, retrieving from global LATEST_ACCESS_TOKEN.")
        token_key = LATEST_ACCESS_TOKEN
    
    if token_key is None:
        token_key = get_local_dev_token()


    logger.info(f"token_key is not None. token_key: {token_key}")
    
    if token_key:
        logger.info(f"Token found/retrieved. Storing in tool_context.state and global variable.")
        
        # Store in the tool_context.state for the current execution chain (temp: scope)
        tool_context.state[token_state_key] = token_key
        # Update the global variable for persistence across turns (local session fix)
        LATEST_ACCESS_TOKEN = token_key
        logger.info("Current tool_context.state after adding token: %s", tool_context.state.to_dict())
    else:
        logger.warning("No valid tokens found and could not generate a new one.")
        return None
    
    pattern = re.compile(r'.*'+auth_id+'.*')
    # logger.info("Checking for pattern using regex: %s", pattern.pattern)

    state_dict = tool_context.state.to_dict()
    # logger.info("Current tool context state keys: %s", state_dict)
    matched_auth = {key: value for key, value in state_dict.items() if pattern.match(key)}
    if len(matched_auth) > 0:
        token_key_name = list(matched_auth.keys())[0]
    else:
        logger.warning("No valid tokens found")
        return None
        
    access_token = state_dict[token_key_name]
    dynamic_auth_config = {dynamic_auth_internal_key: access_token}
    args[dynamic_auth_param_name] = json.dumps(dynamic_auth_config)
    logger.info("Injected dynamic_auth_config into args.")
    return None


# This agent is a sub-agent responsible for interacting with the BigQuery
# Application Integration connector. It uses the `dynamic_token_injection`
# callback to handle authentication for its tool calls.
cloud_bqoauth_agent = Agent(
    model="gemini-2.5-flash",
    name="cloud_bqoauth_agent",
    instruction=cloud_bqoauth_agent_instructions,
    tools=[app_int_cloud_bqoauth_connector],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
    before_tool_callback=dynamic_token_injection,
)

# This is the main agent that the user interacts with. It doesn't have any
# direct tools but instead delegates tasks to its sub-agents. In this case, it
# delegates BigQuery-related questions to the `cloud_bqoauth_agent`.
root_agent = Agent(
    model="gemini-2.5-flash",
    name="RootAgent",
    instruction=root_agent_instructions,
    tools=[AgentTool(agent=cloud_bqoauth_agent)],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)

app = App(root_agent=root_agent, name="app")
