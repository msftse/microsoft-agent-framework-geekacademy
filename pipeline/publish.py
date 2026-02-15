"""Publish content pipeline to Azure AI Foundry.

Usage:  python -m pipeline.publish [--register | --verify]
"""

from __future__ import annotations
import argparse, asyncio, json, os, sys
from pathlib import Path
import httpx
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import WorkflowAgentDefinition
from dotenv import load_dotenv
from pipeline.config import load_settings

YAML = Path(__file__).parent / "content-pipeline.yaml"
AGENT, APP, DEPLOY = (
    "ContentPipeline",
    "content-pipeline-app",
    "content-pipeline-deployment",
)
ARM_V, AI_V = "2025-10-01-preview", "2025-11-15-preview"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    ep = load_settings().project_endpoint.rstrip("/")
    h = ep.split("/")[2]
    sub, rg = (
        os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
        os.environ.get("AZURE_RESOURCE_GROUP", ""),
    )
    acct = os.environ.get("AZURE_ACCOUNT_NAME") or h.split(".")[0]
    proj = os.environ.get("AZURE_PROJECT_NAME") or ep.split("/")[-1]
    assert sub and rg, "AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP required."

    arm = (
        f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{acct}/projects/{proj}"
    )
    ai = f"https://{acct}.services.ai.azure.com/api/projects/{proj}"
    cred = DefaultAzureCredential()

    # -- verify --
    if args.verify:
        hdr = {
            "Authorization": f"Bearer {cred.get_token('https://ai.azure.com/.default').token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=300) as c:
            conv = (
                await c.post(
                    f"{ai}/openai/conversations?api-version={AI_V}",
                    headers=hdr,
                    json={},
                )
            ).json()["id"]
            r = await c.post(
                f"{ai}/openai/responses?api-version={AI_V}",
                headers=hdr,
                json={
                    "input": "Say hello briefly",
                    "agent": {"name": AGENT, "type": "agent_reference"},
                    "store": True,
                    "conversation": {"id": conv},
                },
            )
        assert r.status_code == 200, f"ERROR {r.status_code}: {r.text[:300]}"
        print(json.dumps(r.json(), indent=2)[:2000])
        return

    # -- register --
    v = AIProjectClient(endpoint=ep, credential=cred).agents.create_version(
        agent_name=AGENT, definition=WorkflowAgentDefinition(workflow=YAML.read_text())
    )
    vid = f"{v.name}:{v.version}"
    print(f"Registered {vid}")
    if args.register:
        return

    # -- publish --
    name, ver = vid.rsplit(":", 1)
    hdr = {
        "Authorization": f"Bearer {cred.get_token('https://management.azure.com/.default').token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as c:
        for url, body in [
            (
                f"{arm}/applications/{APP}?api-version={ARM_V}",
                {
                    "properties": {
                        "displayName": "Content Pipeline",
                        "agents": [{"agentName": name}],
                    }
                },
            ),
            (
                f"{arm}/applications/{APP}/agentdeployments/{DEPLOY}?api-version={ARM_V}",
                {
                    "properties": {
                        "deploymentType": "Managed",
                        "protocols": [{"protocol": "responses", "version": "1.0"}],
                        "agents": [{"agentName": name, "agentVersion": ver}],
                    }
                },
            ),
        ]:
            r = await c.put(url, headers=hdr, json=body)
            assert r.status_code in (200, 201), f"ERROR {r.status_code}: {r.text[:300]}"
    print(
        f"Published -> {ai}/applications/{APP}/protocols/openai/responses?api-version={AI_V}"
    )


if __name__ == "__main__":
    asyncio.run(main())
