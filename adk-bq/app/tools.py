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

"""Defines the external tools available to the agent."""

import os
from dotenv import load_dotenv

import google.auth
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset

#from .oauth import oauth2_scheme, oauth2_credential

from .prompts import app_int_cloud_bqoauth_instructions
load_dotenv()


project_id = os.getenv("GOOGLE_CLOUD_PROJECT")


# This toolset connects to a Google Cloud Application Integration connector.
# Application Integration provides a managed, low-code way to connect to various
# enterprise systems and Google Cloud services.
# In this case, it's configured to connect to a BigQuery database, allowing the
# agent to execute a custom query. The specific connection details are loaded
# from environment variables.
app_int_cloud_bqoauth_connector = ApplicationIntegrationToolset(
    project=project_id,
    location=os.getenv("BQ_CONNECTION_REGION"),
    connection=os.getenv("BQ_CONNECTION_NAME"),
    actions=["ExecuteCustomQuery"],
    tool_name_prefix="bqcitibike",
    tool_instructions=app_int_cloud_bqoauth_instructions,
    # auth_credential=oauth2_credential,
    # auth_scheme=oauth2_scheme,
)