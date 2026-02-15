"""Publish content pipeline to Azure AI Foundry.

Usage:  python -m pipeline.publish [--register | --verify]
"""

from __future__ import annotations
import argparse, asyncio, os, sys
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
_cred = DefaultAzureCredential()


def _env():
    load_dotenv()
    ep = load_settings().project_endpoint.rstrip("/")
    h = ep.split("/")[2]
    e = dict(
        sub=os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
        rg=os.environ.get("AZURE_RESOURCE_GROUP", ""),
        acct=os.environ.get("AZURE_ACCOUNT_NAME") or h.split(".")[0],
        proj=os.environ.get("AZURE_PROJECT_NAME") or ep.split("/")[-1],
        ep=ep,
    )
    if not e["sub"] or not e["rg"]:
        sys.exit("AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP required.")
    return e


def _arm(e):
    return (
        f"https://management.azure.com/subscriptions/{e['sub']}/resourceGroups/{e['rg']}"
        f"/providers/Microsoft.CognitiveServices/accounts/{e['acct']}/projects/{e['proj']}"
    )


def _ai(e):
    return f"https://{e['acct']}.services.ai.azure.com/api/projects/{e['proj']}"


async def register(env):
    v = AIProjectClient(endpoint=env["ep"], credential=_cred).agents.create_version(
        agent_name=AGENT, definition=WorkflowAgentDefinition(workflow=YAML.read_text())
    )
    print(f"Registered {v.name}:{v.version}")
    return f"{v.name}:{v.version}"


async def publish(env, vid):
    name, ver = vid.rsplit(":", 1) if ":" in vid else (AGENT, "1")
    h = {
        "Authorization": f"Bearer {_cred.get_token('https://management.azure.com/.default').token}",
        "Content-Type": "application/json",
    }
    b = _arm(env)
    async with httpx.AsyncClient(timeout=60) as c:
        for tag, url, body in [
            (
                "App",
                f"{b}/applications/{APP}?api-version={ARM_V}",
                {
                    "properties": {
                        "displayName": "Content Pipeline",
                        "agents": [{"agentName": name}],
                    }
                },
            ),
            (
                "Deploy",
                f"{b}/applications/{APP}/agentdeployments/{DEPLOY}?api-version={ARM_V}",
                {
                    "properties": {
                        "displayName": "Content Pipeline Deployment",
                        "deploymentType": "Managed",
                        "protocols": [{"protocol": "responses", "version": "1.0"}],
                        "agents": [{"agentName": name, "agentVersion": ver}],
                    }
                },
            ),
        ]:
            r = await c.put(url, headers=h, json=body)
            if r.status_code not in (200, 201):
                sys.exit(f"{tag} ERROR {r.status_code}: {r.text[:300]}")
    print(
        f"Published -> {_ai(env)}/applications/{APP}/protocols/openai/responses?api-version={AI_V}"
    )


async def verify(env):
    h = {
        "Authorization": f"Bearer {_cred.get_token('https://ai.azure.com/.default').token}",
        "Content-Type": "application/json",
    }
    b = _ai(env)
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(
            f"{b}/openai/conversations?api-version={AI_V}", headers=h, json={}
        )
        if r.status_code != 200:
            return print(f"ERROR creating conversation: {r.status_code}")
        conv = r.json()["id"]
        print(f"Invoking '{AGENT}'...")
        r = await c.post(
            f"{b}/openai/responses?api-version={AI_V}",
            headers=h,
            json={
                "input": "Say hello briefly",
                "agent": {"name": AGENT, "type": "agent_reference"},
                "store": True,
                "conversation": {"id": conv},
            },
        )
    if r.status_code != 200:
        return print(f"ERROR {r.status_code}: {r.text[:300]}")
    data = r.json()
    print(f"OK — status={data.get('status')}, outputs={len(data.get('output', []))}")
    for o in data.get("output", []):
        a = o.get("created_by", {}).get("agent", {}).get("name", "?")
        if o["type"] == "message":
            for ct in o.get("content", []):
                if ct.get("type") == "output_text":
                    print(f"  [{a}] {ct['text'][:200]}")
        elif o["type"] == "workflow_action":
            print(f"  [workflow] {o['action_id']} status={o['status']}")


async def main():
    ap = argparse.ArgumentParser(
        description="Publish content pipeline to Azure AI Foundry"
    )
    ap.add_argument("--register", action="store_true", help="Register only")
    ap.add_argument("--verify", action="store_true", help="Verify endpoint")
    args = ap.parse_args()
    env = _env()
    if args.verify:
        return await verify(env)
    vid = await register(env)
    if not args.register:
        await publish(env, vid)
        print("Verify: python -m pipeline.publish --verify")


if __name__ == "__main__":
    asyncio.run(main())
