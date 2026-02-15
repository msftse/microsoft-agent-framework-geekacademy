"""FastAPI server exposing the content pipeline and individual agents as SSE endpoints.

Uses the new Azure AI Foundry Agent SDK.  Agents are registered as persistent
resources and are visible in the AI Foundry portal.

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
from agent_framework import AgentResponseUpdate
from agent_framework.azure import AzureAIProjectAgentProvider

from pipeline.config import load_settings
from pipeline.tracing import setup_tracing
from pipeline.tools import create_learn_tool, create_github_tool
from pipeline.agents import create_researcher, create_writer, create_reviewer
from pipeline.workflow import build_pipeline
from pipeline.memory import ensure_memory_store
from prompts import load_prompt


# ---------------------------------------------------------------------------
# Shared state — initialized once at startup
# ---------------------------------------------------------------------------


class AppState:
    """Holds resources created during server lifespan."""

    def __init__(self):
        self.credential: DefaultAzureCredential | None = None
        self.agents: dict = {}


state = AppState()


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent provider, MCP tools, memory store, agents, and pipeline on startup."""
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

    # Enter MCP tool context managers
    await learn_tool.__aenter__()
    if github_tool:
        await github_tool.__aenter__()

    # Agents are eagerly registered in AI Foundry on creation
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
    """Stream the full pipeline as SSE events.

    A fresh Workflow is built per request because Workflow instances contain
    state that is preserved across calls (per Microsoft docs).  For independent
    concurrent runs we must create separate Workflow instances.

    The SequentialBuilder workflow emits lifecycle events (executor_invoked,
    executor_completed) but not per-token AgentResponseUpdate events.  We
    extract each agent's response text from the executor_completed event's
    message list and stream it to the client.
    """
    # Build a fresh pipeline per request for state isolation
    pipeline = build_pipeline(
        state.agents["researcher"],
        state.agents["writer"],
        state.agents["reviewer"],
    )

    message = load_prompt("pipeline_message", topic=topic)
    current_agent = None
    seen_message_count = 0  # track how many messages we've already seen

    stream = pipeline.run(message, stream=True)
    async for event in stream:
        executor_id = getattr(event, "executor_id", None)

        # Agent handoff
        if event.type == "executor_invoked" and executor_id not in (
            "input-conversation",
            "end",
            None,
        ):
            current_agent = executor_id
            print(f"[pipeline] {executor_id} started")
            yield {
                "event": "agent",
                "data": json.dumps({"agent": current_agent}),
            }

        # Agent completed — extract new assistant messages and stream text
        if event.type == "executor_completed" and executor_id not in (
            "input-conversation",
            "end",
            None,
        ):
            messages = event.data if isinstance(event.data, list) else []
            # Only emit new messages (ones added by the current agent)
            new_messages = messages[seen_message_count:]
            seen_message_count = len(messages)

            text_count = 0
            for msg in new_messages:
                role = getattr(msg, "role", None)
                text = getattr(msg, "text", None)
                if role == "assistant" and text:
                    text_count += 1
                    yield {
                        "event": "text",
                        "data": json.dumps({"agent": current_agent, "text": text}),
                    }
            if text_count == 0 and len(new_messages) > 0:
                # Debug: log first few messages to understand why no text was extracted
                for i, msg in enumerate(new_messages[:5]):
                    t = getattr(msg, "text", None)
                    t_preview = repr(t[:80]) if t else repr(t)
                    print(
                        f"[pipeline] DEBUG {executor_id} msg[{i}]: "
                        f"role={getattr(msg, 'role', None)} "
                        f"text={t_preview} type={type(msg).__name__}"
                    )
            print(
                f"[pipeline] {executor_id} completed: {text_count} text chunks "
                f"streamed (from {len(new_messages)} new messages)"
            )

    yield {"event": "done", "data": json.dumps({"status": "complete"})}


async def stream_agent(agent, message: str, agent_name: str):
    """Stream a single agent's response as SSE events.

    Uses agent.run(message, stream=True) which returns a ResponseStream.
    Each chunk is an AgentResponseUpdate with a .text property.
    """
    yield {
        "event": "agent",
        "data": json.dumps({"agent": agent_name}),
    }

    stream = agent.run(message, stream=True)
    async for chunk in stream:
        text = getattr(chunk, "text", None)
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
