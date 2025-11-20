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

from fastapi.openapi.models import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows

from .prompts import root_agent_instructions, cloud_bqoauth_agent_instructions
from .tools import app_int_cloud_bqoauth_connector


load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

print("Libraries imported.")

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

auth_id="bq_dynamic_oauth" 
dynamic_auth_param_name = "dynamic_auth_config" # Name of the parameter to inject
dynamic_auth_internal_key = "oauth2_auth_code_flow.access_token" # Internal key for the token

def dynamic_token_injection(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    token_key = None
    # Uncomment when you want to test locally, you must obtain a valid access token yourself.
    tool_context.state['temp:'+auth_id+'_0'] = os.getenv("ADK_ACCESS_TOKEN")
    pattern = re.compile(r'^temp:'+auth_id+'.*')

    state_dict = tool_context.state.to_dict()
    print("Current Tool Context State:", state_dict)
    matched_auth = {key: value for key, value in state_dict.items() if pattern.match(key)}
    if len(matched_auth) > 0:
        token_key = list(matched_auth.keys())[0]
    else:
        print("No valid tokens found")
        return None
    access_token = tool_context.state[token_key]
    dynamic_auth_config = {dynamic_auth_internal_key: access_token}
    args[dynamic_auth_param_name] = json.dumps(dynamic_auth_config)
    return None

# Define the bqoauth Agent with tools and instructions
# cloud_bqoauth_agent = Agent(
#     model="gemini-2.5-flash",
#     name="cloud_bqoauth_agent",
#     instruction=cloud_bqoauth_agent_instructions,
#     tools=[app_int_cloud_bqoauth_connector],
#     generate_content_config=types.GenerateContentConfig(temperature=0.01),
#     before_tool_callback=dynamic_token_injection
# )

# Define the root agent with tools and instructions
root_agent = Agent(
    model="gemini-2.5-flash",
    name="RootAgent",
    instruction=root_agent_instructions,
    tools=[app_int_cloud_bqoauth_connector],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
    before_tool_callback=dynamic_token_injection
)

app = App(root_agent=root_agent, name="app")
