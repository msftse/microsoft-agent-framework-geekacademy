"""A2A Server — exposes the Reviewer agent over the A2A protocol.

Run:  python -m a2a_demo.server
Then:  python -m a2a_demo.client  (in another terminal)
"""

from __future__ import annotations

import asyncio
import uuid

import uvicorn
from azure.identity.aio import AzureCliCredential
from agent_framework.azure import AzureAIAgentClient
from agent_framework import ChatMessage

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    Artifact,
    Part,
    TextPart,
)

from pipeline.config import load_settings

HOST = "localhost"
PORT = 9000

# ── Agent executor: bridges agent-framework → A2A protocol ──────────────


class ReviewerExecutor(AgentExecutor):
    """Runs the Reviewer agent and publishes results to the A2A event queue."""

    def __init__(self, agent) -> None:
        self._agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        task_id = context.task_id or uuid.uuid4().hex
        context_id = context.context_id or uuid.uuid4().hex

        # Signal: working
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.working),
                final=False,
            )
        )

        # Run the agent-framework agent
        response = await self._agent.run(
            ChatMessage(role="user", text=user_input),
        )
        result_text = response.text or ""

        # Publish the result as an artifact
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=Artifact(
                    artifact_id=uuid.uuid4().hex,
                    name="reviewed-article",
                    parts=[Part(root=TextPart(text=result_text))],
                ),
            )
        )

        # Signal: completed
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.completed),
                final=True,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or ""
        context_id = context.context_id or ""
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.canceled),
                final=True,
            )
        )


# ── Build & serve ───────────────────────────────────────────────────────


async def build_app():
    """Create the A2A Starlette app with the Reviewer agent."""
    settings = load_settings()
    credential = AzureCliCredential()

    client = AzureAIAgentClient(
        project_endpoint=settings.project_endpoint,
        model_deployment_name=settings.model_deployment,
        credential=credential,
    )

    reviewer = client.as_agent(
        name="Reviewer",
        instructions=(
            "You are a senior technical editor. Review the provided article for "
            "technical accuracy, clarity, code correctness, and logical flow. "
            "Output the final polished version, fixing any issues found."
        ),
    )

    # Agent card describes this agent to A2A clients
    agent_card = AgentCard(
        name="Reviewer",
        description="Senior technical editor — reviews and polishes developer articles.",
        url=f"http://{HOST}:{PORT}",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="review-article",
                name="Review Article",
                description="Reviews a technical article for accuracy, clarity, and polish.",
                tags=["review", "editing", "technical-writing"],
            )
        ],
    )

    # Wire it all together
    executor = ReviewerExecutor(reviewer)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
    return a2a_app.build()


def main() -> None:
    app = asyncio.run(build_app())
    print(f"\n{'=' * 50}")
    print(f"A2A Reviewer server running at http://{HOST}:{PORT}")
    print(f"Agent card: http://{HOST}:{PORT}/.well-known/agent-card.json")
    print(f"{'=' * 50}\n")
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
