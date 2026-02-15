"""Entry point — wires config, tracing, tools, agents, and workflow together.

Uses the new Azure AI Foundry Agent SDK.  Agents are registered as persistent
resources in the Foundry project and are visible in the portal.
"""

from __future__ import annotations

import asyncio
import sys

from azure.identity.aio import AzureCliCredential
from agent_framework import AgentResponseUpdate
from agent_framework.azure import AzureAIProjectAgentProvider

from pipeline.config import load_settings
from pipeline.tracing import setup_tracing
from pipeline.tools import create_learn_tool, create_github_tool
from pipeline.agents import create_researcher, create_writer, create_reviewer
from pipeline.workflow import build_pipeline
from pipeline.memory import ensure_memory_store
from prompts import load_prompt

DEFAULT_TOPIC = "Azure Functions serverless computing"


async def main() -> None:
    # 1. Load config and setup tracing
    settings = load_settings()
    setup_tracing(settings)

    # 2. Create Azure AI Foundry agent provider (uses async credential)
    credential = AzureCliCredential()

    # Create memory store if configured
    memory_store_name = None
    if settings.memory_chat_model and settings.memory_embedding_model:
        memory_store_name = await ensure_memory_store(
            endpoint=settings.project_endpoint,
            credential=credential,
            store_name=settings.memory_store_name,
            chat_model=settings.memory_chat_model,
            embedding_model=settings.memory_embedding_model,
        )

    async with AzureAIProjectAgentProvider(
        project_endpoint=settings.project_endpoint,
        credential=credential,
    ) as provider:
        # 3. Start MCP tool servers
        learn_tool = create_learn_tool()
        github_tool = (
            create_github_tool(settings.github_token) if settings.github_token else None
        )
        tools = [learn_tool] + ([github_tool] if github_tool else [])

        async with learn_tool:
            if github_tool:
                await github_tool.__aenter__()

            # 4. Create agents — each is registered in AI Foundry
            researcher = await create_researcher(
                provider,
                tools=tools,
                memory_store_name=memory_store_name,
            )
            writer = await create_writer(provider, memory_store_name=memory_store_name)
            reviewer = await create_reviewer(
                provider, memory_store_name=memory_store_name
            )

            # 5. Build sequential pipeline
            pipeline = build_pipeline(researcher, writer, reviewer)

            # 6. Get topic from user
            topic = (
                input(f"\nEnter a topic [{DEFAULT_TOPIC}]: ").strip() or DEFAULT_TOPIC
            )
            print(f"\n{'=' * 60}")
            print(f"Running content pipeline for: {topic}")
            print(f"{'=' * 60}\n")

            # 7. Stream output, showing agent handoffs
            message = load_prompt("pipeline_message", topic=topic)
            last_executor_id = None

            async for event in pipeline.run(message, stream=True):
                # Agent handoff: show when a new executor starts
                if event.type == "executor_invoked":
                    executor_id = getattr(event, "executor_id", None)
                    if executor_id not in ("input-conversation", "end", None):
                        if last_executor_id is not None:
                            print(f"\n{'-' * 40}")
                        print(f"\n[{executor_id}]:")
                        last_executor_id = executor_id

                # Streaming text tokens from agents
                if event.type == "output" and isinstance(
                    event.data, AgentResponseUpdate
                ):
                    text = str(event.data)
                    if text:
                        print(text, end="", flush=True)

            print(f"\n\n{'=' * 60}")
            print("Pipeline complete!")

            if github_tool:
                await github_tool.__aexit__(None, None, None)

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
