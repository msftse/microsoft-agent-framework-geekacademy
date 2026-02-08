"""FastAPI server exposing the content pipeline and individual agents as SSE endpoints.

Run:  python -m api.server
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from azure.identity.aio import AzureCliCredential
from agent_framework.azure import AzureAIAgentClient

from pipeline.config import load_settings
from pipeline.tracing import setup_tracing
from pipeline.tools import create_learn_tool, create_github_tool
from pipeline.agents import create_researcher, create_writer, create_reviewer
from pipeline.workflow import build_pipeline


# ---------------------------------------------------------------------------
# Shared state — initialized once at startup
# ---------------------------------------------------------------------------


class AppState:
    """Holds resources created during server lifespan."""

    def __init__(self):
        self.credential: AzureCliCredential | None = None
        self.agents: dict = {}
        self.pipeline = None


state = AppState()


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent client, MCP tools, agents, and pipeline on startup."""
    settings = load_settings()
    setup_tracing(settings)

    state.credential = AzureCliCredential()
    client = AzureAIAgentClient(
        project_endpoint=settings.project_endpoint,
        model_deployment_name=settings.model_deployment,
        credential=state.credential,
    )

    learn_tool = create_learn_tool()
    github_tool = create_github_tool(settings.github_token)

    # Enter MCP tool context managers
    await learn_tool.__aenter__()
    await github_tool.__aenter__()

    researcher = create_researcher(client, tools=[learn_tool, github_tool])
    writer = create_writer(client)
    reviewer = create_reviewer(client)

    state.agents = {
        "researcher": researcher,
        "writer": writer,
        "reviewer": reviewer,
    }
    state.pipeline = build_pipeline(researcher, writer, reviewer)

    print("[api] Server ready — agents and pipeline initialized")
    yield

    # Cleanup
    await github_tool.__aexit__(None, None, None)
    await learn_tool.__aexit__(None, None, None)
    if state.credential:
        await state.credential.close()
    print("[api] Server shut down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Content Pipeline API",
    description="Multi-agent content pipeline with SSE streaming",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class TopicRequest(BaseModel):
    topic: str = "Azure Functions serverless computing"


class MessageRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


async def stream_pipeline(topic: str):
    """Stream the full pipeline as SSE events."""
    message = f"Write a technical article about: {topic}"
    current_agent = None

    async for event in state.pipeline.run_stream(message):
        event_type = type(event).__name__
        executor_id = getattr(event, "executor_id", None)

        # Agent handoff
        if event_type == "ExecutorInvokedEvent" and executor_id not in (
            "input-conversation",
            "end",
        ):
            current_agent = executor_id
            yield {
                "event": "agent",
                "data": json.dumps({"agent": current_agent}),
            }

        # Text token
        if event_type == "AgentRunUpdateEvent":
            data = getattr(event, "data", None)
            text = getattr(data, "text", None) if data else None
            if text:
                yield {
                    "event": "text",
                    "data": json.dumps({"agent": current_agent, "text": str(text)}),
                }

    yield {"event": "done", "data": json.dumps({"status": "complete"})}


async def stream_agent(agent, message: str, agent_name: str):
    """Stream a single agent's response as SSE events."""
    yield {
        "event": "agent",
        "data": json.dumps({"agent": agent_name}),
    }

    async for update in agent.run_stream(message):
        text = getattr(update, "text", None)
        if text:
            yield {
                "event": "text",
                "data": json.dumps({"agent": agent_name, "text": str(text)}),
            }

    yield {"event": "done", "data": json.dumps({"status": "complete"})}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "agents": list(state.agents.keys()),
        "pipeline": state.pipeline is not None,
    }


@app.post("/api/pipeline")
async def run_pipeline(request: TopicRequest):
    """Run the full content pipeline (Researcher -> Writer -> Reviewer) with SSE streaming."""
    return EventSourceResponse(stream_pipeline(request.topic))


@app.post("/api/agents/{agent_name}")
async def run_agent(agent_name: str, request: MessageRequest):
    """Run a single agent with SSE streaming."""
    agent = state.agents.get(agent_name.lower())
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available: {list(state.agents.keys())}",
        )
    return EventSourceResponse(stream_agent(agent, request.message, agent_name.lower()))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)
