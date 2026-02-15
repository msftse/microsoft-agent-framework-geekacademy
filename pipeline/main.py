"""Entry point — wires config, tracing, tools, agents, and workflow together.

Uses the new Azure AI Foundry Agent SDK.  Agents are registered as persistent
resources in the Foundry project and are visible in the portal.
"""

from __future__ import annotations

import asyncio
import sys

from azure.identity.aio import AzureCliCredential
from agent_framework import AgentResponseUpdate
from agent_framework.azure import AzureAIAgentClient

from pipeline.config import load_settings
from pipeline.tracing import setup_tracing
from pipeline.tools import create_learn_tool, create_github_tool
from pipeline.agents import create_researcher, create_writer, create_reviewer
from pipeline.workflow import build_pipeline
from prompts import load_prompt

DEFAULT_TOPIC = "Azure Functions serverless computing"


async def main() -> None:
    # 1. Load config and setup tracing
    settings = load_settings()
    setup_tracing(settings)

    # 2. Create Azure AI Foundry agent client (uses async credential)
    credential = AzureCliCredential()

    chat_client = AzureAIAgentClient(
        project_endpoint=settings.project_endpoint,
        model_deployment_name=settings.model_deployment,
        async_credential=credential,
    )

    # 3. Start MCP tool servers
    learn_tool = create_learn_tool()
    github_tool = create_github_tool(settings.github_token)

    async with learn_tool, github_tool:
        # 4. Create agents — each is registered in AI Foundry
        researcher = create_researcher(chat_client, tools=[learn_tool, github_tool])
        writer = create_writer(chat_client)
        reviewer = create_reviewer(chat_client)

        # 5. Build sequential pipeline
        pipeline = build_pipeline(researcher, writer, reviewer)

        # 6. Get topic from user
        topic = input(f"\nEnter a topic [{DEFAULT_TOPIC}]: ").strip() or DEFAULT_TOPIC
        print(f"\n{'=' * 60}")
        print(f"Running content pipeline for: {topic}")
        print(f"{'=' * 60}\n")

        # 7. Stream output, showing agent handoffs
        message = load_prompt("pipeline_message", topic=topic)
        last_executor_id = None

        async for event in pipeline.run_stream(message):
            # Agent handoff: show when a new executor starts
            if event.type == "executor_invoked":
                executor_id = event.executor_id
                if executor_id not in ("input-conversation", "end"):
                    if last_executor_id is not None:
                        print(f"\n{'-' * 40}")
                    print(f"\n[{executor_id}]:")
                    last_executor_id = executor_id

            # Streaming text tokens from agents
            if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
                text = str(event.data)
                if text:
                    print(text, end="", flush=True)

        print(f"\n\n{'=' * 60}")
        print("Pipeline complete!")

    await credential.close()


def run() -> None:
    """Sync entry point for `pyproject.toml` scripts."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)


if __name__ == "__main__":
    run()
