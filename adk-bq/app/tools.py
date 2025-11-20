import os
from dotenv import load_dotenv

import google.auth
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset

from .oauth import oauth2_scheme, oauth2_credential

from .prompts import app_int_cloud_bqoauth_instructions
load_dotenv()


project_id = os.getenv("GOOGLE_CLOUD_PROJECT")


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