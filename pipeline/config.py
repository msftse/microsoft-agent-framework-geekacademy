"""Configuration loader — reads .env and validates required settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_endpoint: str
    model_deployment: str
    github_token: str
    app_insights_connection_string: str | None = None


def load_settings() -> Settings:
    """Load settings from environment / .env file."""
    load_dotenv()

    endpoint = os.environ.get("PROJECT_ENDPOINT", "")
    deployment = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")
    github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")

    if not endpoint:
        raise EnvironmentError("PROJECT_ENDPOINT is required. See .env.example")
    if not github_token:
        raise EnvironmentError(
            "GITHUB_PERSONAL_ACCESS_TOKEN is required. See .env.example"
        )

    return Settings(
        project_endpoint=endpoint,
        model_deployment=deployment,
        github_token=github_token,
        app_insights_connection_string=os.environ.get(
            "APPLICATION_INSIGHTS_CONNECTION_STRING"
        )
        or None,
    )
