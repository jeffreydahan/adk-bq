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

# mypy: disable-error-code="attr-defined,arg-type"
import logging
import os
from typing import Any

import click
import google.auth
import vertexai
from google.adk.artifacts import GcsArtifactService
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
from vertexai._genai.types import AgentEngine, AgentEngineConfig
from vertexai.agent_engines.templates.adk import AdkApp

from app.agent import root_agent
from app.utils.deployment import (
    parse_env_vars,
    print_deployment_success,
    write_deployment_metadata,
)
from app.utils.gcs import create_bucket_if_not_exists
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Set up logging and tracing for the agent engine app."""
        import logging

        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        provider = TracerProvider()
        processor = export.BatchSpanProcessor(
            CloudTraceLoggingSpanExporter(
                project_id=os.environ.get("GOOGLE_CLOUD_PROJECT")
            )
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent.

        Extends the base operations to include feedback registration functionality.
        """
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback"]
        return operations


def load_env_from_file(file_path: str) -> dict[str, str]:
    """Loads environment variables from a .env file."""
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


@click.command()
@click.option(
    "--project",
    default=None,
    help="GCP project ID (defaults to application default credentials)",
)
@click.option(
    "--location",
    default="us-central1",
    help="GCP region (defaults to us-central1)",
    envvar="GOOGLE_CLOUD_LOCATION",
)
@click.option(
    "--agent-name",
    default="my-awesome-agent",
    help="Name for the agent engine",
    envvar="ADK_AGENT_NAME",
)
@click.option(
    "--description",
    default="a helpful and awesome agent",
    envvar="ADK_AGENT_DESCRIPTION",
    help="Description for the agent engine",
)
@click.option(
    "--requirements-file",
    default=".requirements.txt",
    help="Path to requirements.txt file",
)
@click.option(
    "--extra-packages",
    multiple=True,
    default=["./app"],
    help="Additional packages to include",
)
@click.option(
    "--set-env-vars",
    default=None,
    help="Comma-separated list of environment variables in KEY=VALUE format",
)
@click.option(
    "--service-account",
    default=None,
    help="Service account email to use for the agent engine",
)
@click.option(
    "--staging-bucket-uri",
    default=None,
    help="GCS bucket URI for staging files (defaults to gs://{project}-agent-engine)",
)
@click.option(
    "--artifacts-bucket-name",
    default=None,
    help="GCS bucket name for artifacts (defaults to gs://{project}-agent-engine)",
)
def deploy_agent_engine_app(
    project: str | None,
    location: str,
    agent_name: str,
    description: str,
    requirements_file: str,
    extra_packages: tuple[str, ...],
    set_env_vars: str | None,
    service_account: str | None,
    staging_bucket_uri: str | None,
    artifacts_bucket_name: str | None,
) -> AgentEngine:
    """Deploy the agent engine app to Vertex AI."""

    logging.basicConfig(level=logging.INFO)

    # Load environment variables from .env file in the parent directory
    dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_vars_from_file = load_env_from_file(dotenv_path)

    # Parse environment variables if provided
    env_vars_from_cli = parse_env_vars(set_env_vars)

    # Merge environment variables, with CLI overriding file
    env_vars = {**env_vars_from_file, **env_vars_from_cli}

    # Exclude reserved environment variables
    reserved_vars = ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]
    for var in reserved_vars:
        if var in env_vars:
            del env_vars[var]

    if not project:
        _, project = google.auth.default()
    if not staging_bucket_uri:
        staging_bucket_uri = f"gs://{project}-agent-engine"
    if not artifacts_bucket_name:
        artifacts_bucket_name = f"{project}-agent-engine"
    create_bucket_if_not_exists(
        bucket_name=artifacts_bucket_name, project=project, location=location
    )
    create_bucket_if_not_exists(
        bucket_name=staging_bucket_uri, project=project, location=location
    )

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 DEPLOYING AGENT TO VERTEX AI AGENT ENGINE 🤖         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    extra_packages_list = list(extra_packages)

    # Initialize vertexai client
    client = vertexai.Client(
        project=project,
        location=location,
    )
    vertexai.init(project=project, location=location)

    # Read requirements
    with open(requirements_file) as f:
        requirements = f.read().strip().split("\n")
    agent_engine = AgentEngineApp(
        agent=root_agent,
        artifact_service_builder=lambda: GcsArtifactService(
            bucket_name=artifacts_bucket_name
        ),
    )
    # Set worker parallelism to 1
    env_vars["NUM_WORKERS"] = "1"

    # Common configuration for both create and update operations
    labels: dict[str, str] = {}

    config = AgentEngineConfig(
        display_name=agent_name,
        description=description,
        extra_packages=extra_packages_list,
        env_vars=env_vars,
        service_account=service_account,
        requirements=requirements,
        staging_bucket=staging_bucket_uri,
        labels=labels,
        gcs_dir_name=agent_name,
    )

    agent_config = {
        "agent": agent_engine,
        "config": config,
    }
    logging.info(f"Agent config: {agent_config}")

    # Check if an agent with this name already exists
    existing_agents = list(client.agent_engines.list())
    matching_agents = [
        agent
        for agent in existing_agents
        if agent.api_resource.display_name == agent_name
    ]

    if matching_agents:
        # Update the existing agent with new configuration
        logging.info(f"\n📝 Updating existing agent: {agent_name}")
        remote_agent = client.agent_engines.update(
            name=matching_agents[0].api_resource.name, **agent_config
        )
    else:
        # Create a new agent if none exists
        logging.info(f"\n🚀 Creating new agent: {agent_name}")
        remote_agent = client.agent_engines.create(**agent_config)

    write_deployment_metadata(remote_agent)
    print_deployment_success(remote_agent, location, project)

    return remote_agent


if __name__ == "__main__":
    deploy_agent_engine_app()
