"""Configuration loader — reads .env and validates required settings.

Environment variables follow the Azure AI Foundry convention:
  AZURE_AI_PROJECT_ENDPOINT  – AI Foundry project endpoint
  AZURE_AI_MODEL_DEPLOYMENT_NAME – model deployment (e.g. gpt-4o)
  GITHUB_PERSONAL_ACCESS_TOKEN – for the GitHub MCP tool
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_endpoint: str
    model_deployment: str
    github_token: str | None = None
    app_insights_connection_string: str | None = None
    # Memory search
    memory_chat_model: str | None = None
    memory_embedding_model: str | None = None
    memory_store_name: str = "geektime_pipeline_memory"


def load_settings() -> Settings:
    """Load settings from environment / .env file."""
    load_dotenv()

    # Support both old (PROJECT_ENDPOINT) and new (AZURE_AI_PROJECT_ENDPOINT) env var names
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get(
        "PROJECT_ENDPOINT", ""
    )
    deployment = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.environ.get(
        "MODEL_DEPLOYMENT_NAME", "gpt-4o"
    )
    github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or None

    if not endpoint:
        raise EnvironmentError(
            "AZURE_AI_PROJECT_ENDPOINT (or PROJECT_ENDPOINT) is required. See .env.example"
        )

    return Settings(
        project_endpoint=endpoint,
        model_deployment=deployment,
        github_token=github_token,
        app_insights_connection_string=os.environ.get(
            "APPLICATION_INSIGHTS_CONNECTION_STRING"
        )
        or None,
        memory_chat_model=os.environ.get("AZURE_AI_CHAT_MODEL_DEPLOYMENT_NAME") or None,
        memory_embedding_model=os.environ.get(
            "AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME"
        )
        or None,
        memory_store_name=os.environ.get(
            "AZURE_AI_MEMORY_STORE_NAME", "geektime_pipeline_memory"
        ),
    )
