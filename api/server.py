"""FastAPI server exposing the content pipeline and individual agents as SSE endpoints.

Runs the published ContentPipeline workflow agent via the Foundry Responses API
so that every request produces traces visible in the AI Foundry portal.

Run:  python -m api.server
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

from pipeline.config import load_settings
from pipeline.tracing import setup_tracing
from pipeline.tools import create_learn_tool, create_github_tool
from pipeline.agents import create_researcher, create_writer, create_reviewer
from pipeline.memory import ensure_memory_store
from prompts import load_prompt

# Workflow agent registered in Foundry (name matches pipeline/content-pipeline.yaml)
WORKFLOW_AGENT = "ContentPipeline"

# The three sub-agents in execution order (must match the YAML workflow)
AGENT_STEPS = ["Researcher", "Writer", "Reviewer"]


# ---------------------------------------------------------------------------
# Shared state — initialized once at startup
# ---------------------------------------------------------------------------


class AppState:
    """Holds resources created during server lifespan."""

    def __init__(self):
        self.credential = None
        self.project_client = None
        self.openai_client = None
        self.agents: dict = {}


state = AppState()


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent provider, MCP tools, memory store, agents, and Foundry client."""
    settings = load_settings()
    setup_tracing(settings)

    state.credential = DefaultAzureCredential()

    # Create memory store if memory config is provided
    memory_store_name = None
    if settings.memory_chat_model and settings.memory_embedding_model:
        memory_store_name = await ensure_memory_store(
            endpoint=settings.project_endpoint,
            credential=state.credential,
            store_name=settings.memory_store_name,
            chat_model=settings.memory_chat_model,
            embedding_model=settings.memory_embedding_model,
        )
    else:
        print(
            "[api] Memory disabled — set AZURE_AI_CHAT_MODEL_DEPLOYMENT_NAME and "
            "AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME to enable"
        )

    # Agent provider — registers sub-agents in Foundry on startup
    from agent_framework.azure import AzureAIProjectAgentProvider

    provider = AzureAIProjectAgentProvider(
        project_endpoint=settings.project_endpoint,
        credential=state.credential,
    )
    await provider.__aenter__()

    learn_tool = create_learn_tool()
    github_tool = (
        create_github_tool(settings.github_token) if settings.github_token else None
    )
    tools = [learn_tool] + ([github_tool] if github_tool else [])

    await learn_tool.__aenter__()
    if github_tool:
        await github_tool.__aenter__()

    model = settings.model_deployment
    researcher = await create_researcher(
        provider,
        tools=tools,
        model=model,
        memory_store_name=memory_store_name,
    )
    writer = await create_writer(
        provider, model=model, memory_store_name=memory_store_name
    )
    reviewer = await create_reviewer(
        provider, model=model, memory_store_name=memory_store_name
    )

    state.agents = {
        "researcher": researcher,
        "writer": writer,
        "reviewer": reviewer,
    }

    # Foundry OpenAI client — used to invoke the published workflow agent
    state.project_client = AIProjectClient(
        endpoint=settings.project_endpoint,
        credential=state.credential,
    )
    state.openai_client = state.project_client.get_openai_client()

    tools_info = "learn" + (", github" if github_tool else "")
    print(
        f"[api] Server ready — agents registered in AI Foundry (tools: {tools_info})"
        + (f" (memory: {memory_store_name})" if memory_store_name else "")
    )
    yield

    # Cleanup
    if github_tool:
        await github_tool.__aexit__(None, None, None)
    await learn_tool.__aexit__(None, None, None)
    await provider.close()
    if state.openai_client:
        await state.openai_client.close()
    if state.project_client:
        await state.project_client.close()
    if state.credential:
        await state.credential.close()
    print("[api] Server shut down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Content Pipeline API",
    description="Multi-agent content pipeline with SSE streaming (AI Foundry)",
    version="0.2.0",
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
    """Stream the ContentPipeline workflow agent via Foundry Responses API.

    Creates a conversation, sends the topic as input, and streams the response.
    The workflow runs Researcher -> Writer -> Reviewer server-side on Foundry.
    Each response.output_item.done with type "message" marks a completed agent step.
    Text is streamed token-by-token via response.output_text.delta events.
    """
    oc = state.openai_client
    message = load_prompt("pipeline_message", topic=topic)

    # Create a conversation so the workflow agents share context
    conversation = await oc.conversations.create()
    print(f"[pipeline] Conversation {conversation.id} created for topic: {topic}")

    # Track which agent step we're on (based on completed message outputs)
    step_idx = 0
    current_agent = AGENT_STEPS[0]

    # Signal first agent
    yield {"event": "agent", "data": json.dumps({"agent": current_agent})}
    print(f"[pipeline] {current_agent} started")

    stream = await oc.responses.create(
        input=message,
        conversation=conversation.id,
        extra_body={
            "agent": {"name": WORKFLOW_AGENT, "type": "agent_reference"},
            "stream": True,
        },
        stream=True,
    )

    async for event in stream:
        if event.type == "response.output_text.delta":
            yield {
                "event": "text",
                "data": json.dumps({"agent": current_agent, "text": event.delta}),
            }

        elif event.type == "response.output_item.done":
            item = event.item
            # Each completed message output = one agent step done
            if getattr(item, "type", None) == "message":
                print(f"[pipeline] {current_agent} completed")
                step_idx += 1
                if step_idx < len(AGENT_STEPS):
                    current_agent = AGENT_STEPS[step_idx]
                    yield {
                        "event": "agent",
                        "data": json.dumps({"agent": current_agent}),
                    }
                    print(f"[pipeline] {current_agent} started")

        elif event.type == "response.completed":
            print(f"[pipeline] Workflow completed")

    yield {"event": "done", "data": json.dumps({"status": "complete"})}


async def stream_agent(agent_name: str, message: str):
    """Stream a single registered agent's response via Foundry Responses API."""
    oc = state.openai_client

    yield {"event": "agent", "data": json.dumps({"agent": agent_name})}

    stream = await oc.responses.create(
        input=message,
        extra_body={
            "agent": {"name": agent_name.capitalize(), "type": "agent_reference"},
            "stream": True,
        },
        stream=True,
    )

    async for event in stream:
        if event.type == "response.output_text.delta":
            yield {
                "event": "text",
                "data": json.dumps({"agent": agent_name, "text": event.delta}),
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
    return EventSourceResponse(stream_agent(agent_name.lower(), request.message))


# ---------------------------------------------------------------------------
# Frontend — serve static files
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    """Serve the frontend single-page app."""
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)
