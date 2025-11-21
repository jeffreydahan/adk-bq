# ADK BigQuery Agent

This project contains a GenAI agent built with the Google Agent Development Kit (ADK). The agent is designed to interact with Google BigQuery through an Application Integration connector, allowing users to query datasets using natural language.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10+
- [Google Cloud SDK](https://cloud.google.com/sdk/install)
- `uv` (The installation script will handle this if not present)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd adk-bq
    ```

2.  **Install dependencies:**
    This command will install all necessary Python packages defined in `pyproject.toml`.
    ```bash
    make install
    ```

3.  **Configure your environment:**
    Create a `.env` file by copying the example file.
    ```bash
    cp .env.example .env
    ```
    Now, open the `.env` file and add your specific configuration details:
    - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID.
    - `BQ_AUTHORIZATION_ID`: The Authorization ID for the BigQuery connector in Google Cloud Application Integration.

## Running the Agent Locally

To test the agent on your local machine, you can use the ADK's built-in web playground.

1.  **Start the playground:**
    ```bash
    make playground
    ```

2.  **Interact with the agent:**
    - Open your web browser to `http://localhost:8501`.
    - In the playground interface, make sure to select the `app` folder from the dropdown menu to interact with this agent.
    - You can now send messages to the agent, for example: "What are the most popular datasets in BigQuery?"

## Testing and Code Quality

-   **Run tests:**
    To execute the unit and integration tests, run:
    ```bash
    make test
    ```

-   **Lint your code:**
    To check for code quality and formatting issues, run:
    ```bash
    make lint
    ```

## Deployment

This agent is configured for deployment to Google Cloud.

-   **Deploy to Agent Engine:**
    The `make deploy` command will package the agent and deploy it to Agent Engine.
    ```bash
    make deploy
    ```

-   **Development Environment:**
    You can provision a separate development environment in GCP using Terraform.
    ```bash
    make setup-dev-env
    ```