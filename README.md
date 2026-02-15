<p align="center">
  <img src="assests/banner.jpg" alt="Geek Academy - Become an AI Architect with AI-Powered Tools from Microsoft and GitHub" width="100%">
</p>

<h1 align="center">Microsoft Agent Framework - Multi-Agent Content Pipeline</h1>

<p align="center">
  <strong>A hands-on POC demonstrating multi-agent orchestration with MCP tools, A2A protocol, and Azure AI Foundry</strong>
</p>

<p align="center">
  <a href="#architecture">Architecture</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#docker">Docker</a> &bull;
  <a href="#publish-to-foundry">Publish</a> &bull;
  <a href="#api-server--frontend">API & Frontend</a> &bull;
  <a href="#a2a-protocol-demo">A2A Demo</a> &bull;
  <a href="#evaluation">Evaluation</a> &bull;
  <a href="#ci--evaluation-gate">CI</a> &bull;
  <a href="#tracing--observability">Tracing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT">
  <img src="https://img.shields.io/badge/Azure%20AI-Foundry-0078D4.svg" alt="Azure AI Foundry">
  <img src="https://img.shields.io/badge/Microsoft-Agent%20Framework-5C2D91.svg" alt="Microsoft Agent Framework">
  <img src="https://img.shields.io/badge/MCP-Tools-FF6600.svg" alt="MCP Tools">
  <img src="https://img.shields.io/badge/A2A-Protocol-8B5CF6.svg" alt="A2A Protocol">
  <a href="https://github.com/msftse/microsoft-agent-framework-geekacademy/actions/workflows/evaluation.yml"><img src="https://github.com/msftse/microsoft-agent-framework-geekacademy/actions/workflows/evaluation.yml/badge.svg" alt="Evaluation Gate"></a>
</p>

---

## Deploy to Azure

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmsftse%2Fmicrosoft-agent-framework-geekacademy%2Fmain%2Fazuredeploy.json)

> Deploys an Azure AI Foundry project with a `gpt-4o` model deployment and Application Insights for tracing.

---

## Overview

A **multi-agent content creation pipeline** built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). Three AI agents collaborate sequentially — Researcher, Writer, Reviewer — to produce technical articles. Agents are registered as **persistent resources** in Azure AI Foundry (new experience), with optional memory, MCP tools, and a publish-to-Foundry workflow.

### What You'll Learn

- Registering agents in **Azure AI Foundry (new)** via `AzureAIProjectAgentProvider`
- Connecting agents to external tools via **MCP** (Streamable HTTP and stdio)
- Adding **agent memory** with `memory_search` tool and embedding-based recall
- Orchestrating agents with **WorkflowBuilder** (graph-based sequential pipeline)
- **Publishing workflows** to Foundry as Agent Applications with declarative YAML
- Exposing agents via the **A2A (Agent-to-Agent) protocol**
- **Evaluating** outputs with Azure AI Foundry built-in evaluators
- Serving agents as a **REST API with SSE streaming** using FastAPI

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │     WorkflowBuilder          │
                    │   (Sequential Pipeline)      │
                    └─────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌─────────────┐       ┌──────────────┐       ┌──────────────┐
   │  Researcher  │       │    Writer     │       │   Reviewer   │
   │              │       │              │       │              │
   │  Gathers     │──────▶│  Transforms  │──────▶│  Polishes    │
   │  information │       │  into article│       │  final draft │
   └──────┬───────┘       └──────┬───────┘       └──────┬───────┘
          │                      │                      │
    ┌─────┴─────┐          ┌─────┘                ┌─────┘
    ▼           ▼          ▼                      ▼
┌────────┐ ┌────────┐ ┌────────┐            ┌────────┐
│MS Learn│ │ GitHub │ │ Memory │            │ Memory │
│  MCP   │ │  MCP   │ │ Search │            │ Search │
│ (HTTP) │ │(stdio) │ └────────┘            └────────┘
└────────┘ └────────┘
```

| Agent | Role | Tools |
|-------|------|-------|
| **Researcher** | Gathers facts, docs, and code examples | Microsoft Learn MCP, GitHub MCP (optional), memory_search |
| **Writer** | Transforms research into a developer article | memory_search |
| **Reviewer** | Edits for accuracy, clarity, and structure | memory_search |

All agents are registered in the **Azure AI Foundry portal** on startup (kind: `prompt`, versioned as `Researcher:N`, `Writer:N`, `Reviewer:N`).

---

## Prerequisites

- **Python 3.10+**
- **Azure CLI** — logged in (`az login`)
- **Azure AI Foundry project** with a deployed model (e.g., `gpt-4o`)
- **Node.js 18+** — only if using the GitHub MCP tool (optional)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/msftse/microsoft-agent-framework-geekacademy.git
cd microsoft-agent-framework-geekacademy
pip install .
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required
AZURE_AI_PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o

# Optional — agent memory (recommended)
AZURE_AI_CHAT_MODEL_DEPLOYMENT_NAME=gpt-4o
AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME=text-embedding-3-small

# Optional — GitHub MCP tool (requires Node.js)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Optional — tracing
APPLICATION_INSIGHTS_CONNECTION_STRING=
```

### 3. Login and run

```bash
az login
python -m api.server
# Open http://localhost:8000
```

Or run the CLI pipeline directly:

```bash
python -m pipeline.main
```

---

## Docker

Run everything in one command — no local Python or Node.js required.

### Prerequisites

Add service principal credentials to `.env` (since `az login` isn't available in Docker):

```env
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Run

```bash
docker compose up --build
```

Opens on `http://localhost:8000` with the frontend, API, agents, and MCP tools ready.

Or without compose:

```bash
docker build -t maf-poc .
docker run -p 8000:8000 --env-file .env maf-poc
```

---

## Publish to Foundry

Register the pipeline as a **workflow agent** in Azure AI Foundry and publish it as an **Agent Application** with a managed deployment.

### Setup

Add to `.env`:

```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
```

### Publish

```bash
python -m pipeline.publish            # register + publish
python -m pipeline.publish --register # register workflow agent only
python -m pipeline.publish --verify   # invoke workflow and print response
```

The workflow is defined in `pipeline/content-pipeline.yaml` — a declarative CSDL YAML that chains `Researcher -> Writer -> Reviewer` using `InvokeAzureAgent` actions with shared conversation context.

---

## API Server & Frontend

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/pipeline` | Full pipeline (SSE stream) |
| `POST` | `/api/agents/{name}` | Single agent (SSE stream) |

### SSE Events

```
event: agent
data: {"agent": "Researcher"}

event: text
data: {"agent": "Researcher", "text": "Azure Functions is..."}

event: done
data: {"status": "complete"}
```

### Frontend

Single-page chat UI served at `/` with:
- Per-agent chat bubbles with colored borders and avatars
- Pipeline progress indicator (Researcher -> Writer -> Reviewer)
- Word-by-word streaming
- Single Agent mode for direct chat

### Example

```bash
curl -N -X POST http://localhost:8000/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{"topic": "Azure Container Apps"}'
```

---

## A2A Protocol Demo

Exposes the Reviewer agent as a remote service via the [A2A protocol](https://github.com/google/A2A).

```
Terminal 1 (Server)                    Terminal 2 (Client)
┌──────────────────────┐              ┌──────────────────────┐
│  Reviewer Agent      │    A2A       │  A2AAgent            │
│  (Azure AI Foundry)  │◀──JSON-RPC──│  (framework client)  │
│  localhost:9000      │              │                      │
└──────────────────────┘              └──────────────────────┘
```

```bash
# Terminal 1
python -m a2a_demo.server

# Terminal 2
python -m a2a_demo.client
```

---

## Evaluation

Measures pipeline output quality using [Azure AI Foundry evaluators](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/evaluate-generative-ai-app).

| Evaluator | Measures | Scale |
|-----------|----------|-------|
| **Coherence** | Logical flow | 1-5 |
| **Fluency** | Language quality | 1-5 |
| **Relevance** | Addresses the query | 1-5 |

```bash
python -m evaluation.run
```

Results appear in the **Evaluation** tab in Azure AI Foundry.

---

## CI — Evaluation Gate

Every PR to `main` runs `python -m evaluation.ci --threshold 4.0`. If any metric scores below **4.0/5.0**, the PR is blocked.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name |
| `AZURE_TENANT_ID` | Service principal tenant ID |
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |

---

## Tracing & Observability

Set `APPLICATION_INSIGHTS_CONNECTION_STRING` in `.env` for Azure Monitor tracing. Traces appear in the Azure AI Foundry portal showing workflow spans, agent execution, chat completions, and MCP tool calls.

Leave empty for console output.

---

## Project Structure

```
├── pipeline/
│   ├── config.py              # Settings from .env
│   ├── agents.py              # Agent definitions (Researcher, Writer, Reviewer)
│   ├── tools.py               # MCP tool factories (Learn HTTP, GitHub stdio)
│   ├── memory.py              # Memory store creation
│   ├── workflow.py            # WorkflowBuilder pipeline
│   ├── publish.py             # Publish workflow to Foundry
│   ├── content-pipeline.yaml  # Declarative CSDL workflow
│   ├── tracing.py             # OpenTelemetry setup
│   └── main.py                # CLI entry point
├── api/
│   └── server.py              # FastAPI + SSE streaming
├── frontend/
│   └── index.html             # Chat UI (served at /)
├── a2a_demo/
│   ├── server.py              # A2A server (Reviewer)
│   └── client.py              # A2A client
├── evaluation/
│   ├── dataset.jsonl          # 5-sample eval dataset
│   ├── run.py                 # Run evaluators
│   └── ci.py                  # CI gate
├── prompts/                   # Agent system prompts
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Technologies

| Technology | Usage |
|-----------|-------|
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Agent creation, workflows, MCP, A2A |
| [Azure AI Foundry](https://ai.azure.com) | LLM hosting, agent registry, memory, tracing |
| [MCP](https://modelcontextprotocol.io) | Microsoft Learn (HTTP) & GitHub (stdio) tools |
| [A2A Protocol](https://github.com/google/A2A) | Inter-agent communication |
| [FastAPI](https://fastapi.tiangolo.com) | REST API with SSE streaming |
| [Azure AI Evaluation](https://learn.microsoft.com/en-us/python/api/azure-ai-evaluation/) | Coherence, Fluency, Relevance scoring |

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `EnvironmentError: AZURE_AI_PROJECT_ENDPOINT required` | Copy `.env.example` to `.env` and set your endpoint |
| `401 Unauthorized` | Run `az login` to refresh credentials |
| GitHub MCP hangs | Ensure Node.js 18+ is installed; or remove `GITHUB_PERSONAL_ACCESS_TOKEN` to skip |
| Traces not appearing | Check `APPLICATION_INSIGHTS_CONNECTION_STRING`; traces take 1-2 min |
| Docker auth fails | Set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` in `.env` |

---

## License

MIT

---

<p align="center">
  Built for <strong>Geek Academy</strong> — Become an AI Architect with AI-Powered Tools from Microsoft and GitHub
</p>
