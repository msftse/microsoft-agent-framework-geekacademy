"""Publish the content pipeline as a workflow agent in Azure AI Foundry.

Usage:
    python -m pipeline.publish              # register + publish
    python -m pipeline.publish --register   # register workflow agent only
    python -m pipeline.publish --verify     # verify published endpoint
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import WorkflowAgentDefinition
from dotenv import load_dotenv

from pipeline.config import load_settings

YAML_PATH = Path(__file__).parent / "content-pipeline.yaml"
WORKFLOW_AGENT_NAME = "ContentPipeline"
APP_NAME = "content-pipeline-app"
DEPLOY_NAME = "content-pipeline-deployment"
ARM_API = "2025-10-01-preview"
AI_API = "2025-11-15-preview"

_cred = DefaultAzureCredential()


def _token(scope: str) -> str:
    return _cred.get_token(scope).token


def _env() -> dict[str, str]:
    """Load and validate publish env vars."""
    load_dotenv()
    settings = load_settings()
    endpoint = settings.project_endpoint.rstrip("/")
    parts = endpoint.split("/")
    host = parts[2]

    env = {
        "sub": os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
        "rg": os.environ.get("AZURE_RESOURCE_GROUP", ""),
        "account": os.environ.get("AZURE_ACCOUNT_NAME") or host.split(".")[0],
        "project": os.environ.get("AZURE_PROJECT_NAME") or parts[-1],
        "endpoint": endpoint,
    }
    if not env["sub"] or not env["rg"]:
        sys.exit(
            "ERROR: AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP required. See .env.example"
        )
    return env


def _arm_base(env: dict[str, str]) -> str:
    return (
        f"https://management.azure.com/subscriptions/{env['sub']}"
        f"/resourceGroups/{env['rg']}/providers/Microsoft.CognitiveServices"
        f"/accounts/{env['account']}/projects/{env['project']}"
    )


def _ai_base(env: dict[str, str]) -> str:
    return (
        f"https://{env['account']}.services.ai.azure.com/api/projects/{env['project']}"
    )


# -- Step 1: Register workflow agent -----------------------------------------


async def register(env: dict[str, str]) -> str:
    yaml_content = YAML_PATH.read_text()
    client = AIProjectClient(endpoint=env["endpoint"], credential=_cred)

    print(f"Registering workflow agent '{WORKFLOW_AGENT_NAME}'...")
    v = client.agents.create_version(
        agent_name=WORKFLOW_AGENT_NAME,
        definition=WorkflowAgentDefinition(workflow=yaml_content),
    )
    vid = f"{v.name}:{v.version}"
    print(f"  -> {vid} (kind={v.definition.kind})")
    return vid


# -- Step 2: Publish as Agent Application ------------------------------------


async def publish(env: dict[str, str], version_id: str) -> str:
    base = _arm_base(env)
    headers = {
        "Authorization": f"Bearer {_token('https://management.azure.com/.default')}",
        "Content-Type": "application/json",
    }
    agent_name, ver = (
        version_id.rsplit(":", 1) if ":" in version_id else (WORKFLOW_AGENT_NAME, "1")
    )

    async with httpx.AsyncClient(timeout=60) as c:
        # Create application
        print(f"Creating application '{APP_NAME}'...")
        r = await c.put(
            f"{base}/applications/{APP_NAME}?api-version={ARM_API}",
            headers=headers,
            json={
                "properties": {
                    "displayName": "Content Pipeline",
                    "agents": [{"agentName": agent_name}],
                }
            },
        )
        if r.status_code not in (200, 201):
            sys.exit(f"  ERROR {r.status_code}: {r.text[:300]}")
        print(f"  -> {r.json().get('properties', {}).get('baseUrl', 'ok')}")

        # Create deployment
        print(f"Creating deployment '{DEPLOY_NAME}'...")
        r = await c.put(
            f"{base}/applications/{APP_NAME}/agentdeployments/{DEPLOY_NAME}?api-version={ARM_API}",
            headers=headers,
            json={
                "properties": {
                    "displayName": "Content Pipeline Deployment",
                    "deploymentType": "Managed",
                    "protocols": [{"protocol": "responses", "version": "1.0"}],
                    "agents": [{"agentName": agent_name, "agentVersion": ver}],
                }
            },
        )
        if r.status_code not in (200, 201):
            sys.exit(f"  ERROR {r.status_code}: {r.text[:300]}")
        print("  -> ok")

    url = f"{_ai_base(env)}/applications/{APP_NAME}/protocols/openai/responses?api-version={AI_API}"
    print(f"\nEndpoint: {url}")
    return url


# -- Step 3: Verify ----------------------------------------------------------


async def verify(env: dict[str, str]) -> None:
    """Invoke workflow via project-level API (app endpoint is stateless, workflows need conversations)."""
    base = _ai_base(env)
    headers = {
        "Authorization": f"Bearer {_token('https://ai.azure.com/.default')}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(
            f"{base}/openai/conversations?api-version={AI_API}",
            headers=headers,
            json={},
        )
        if r.status_code != 200:
            return print(f"ERROR creating conversation: {r.status_code}")
        conv_id = r.json()["id"]

        print(f"Invoking '{WORKFLOW_AGENT_NAME}' (conv={conv_id[:20]}...)...")
        r = await c.post(
            f"{base}/openai/responses?api-version={AI_API}",
            headers=headers,
            json={
                "input": "Say hello and introduce yourself briefly",
                "agent": {"name": WORKFLOW_AGENT_NAME, "type": "agent_reference"},
                "store": True,
                "conversation": {"id": conv_id},
            },
        )

    if r.status_code != 200:
        return print(f"ERROR {r.status_code}: {r.text[:300]}")

    data = r.json()
    outputs = data.get("output", [])
    print(f"OK — status={data.get('status')}, outputs={len(outputs)}")
    for o in outputs:
        t, agent = (
            o.get("type"),
            o.get("created_by", {}).get("agent", {}).get("name", "?"),
        )
        if t == "message":
            for ct in o.get("content", []):
                if ct.get("type") == "output_text":
                    print(f"  [{agent}] {ct['text'][:200]}")
        elif t == "workflow_action":
            print(f"  [workflow] {o.get('action_id')} status={o.get('status')}")


# -- Main --------------------------------------------------------------------


async def main() -> None:
    ap = argparse.ArgumentParser(
        description="Publish content pipeline to Azure AI Foundry"
    )
    ap.add_argument(
        "--register", action="store_true", help="Register workflow agent only"
    )
    ap.add_argument("--verify", action="store_true", help="Verify published endpoint")
    args = ap.parse_args()

    env = _env()

    if args.verify:
        return await verify(env)

    vid = await register(env)
    if args.register:
        return print("Done (register only).")

    await publish(env, vid)
    print(f"\nVerify: python -m pipeline.publish --verify")


if __name__ == "__main__":
    asyncio.run(main())
