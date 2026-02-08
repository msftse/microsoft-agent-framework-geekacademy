<p align="center">
  <img src="assests/banner.jpg" alt="Geek Academy - Become an AI Architect with AI-Powered Tools from Microsoft and GitHub" width="100%">
</p>

<h1 align="center">Microsoft Agent Framework - Multi-Agent Content Pipeline</h1>

<p align="center">
  <strong>A hands-on POC demonstrating multi-agent orchestration with MCP tools, A2A protocol, and Azure AI Foundry</strong>
</p>

<p align="center">
  <a href="#what-youll-learn">What You'll Learn</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#prerequisites">Prerequisites</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#project-structure">Project Structure</a> &bull;
  <a href="#a2a-protocol-demo">A2A Demo</a> &bull;
  <a href="#evaluation">Evaluation</a> &bull;
  <a href="#api-server">API Server</a> &bull;
  <a href="#frontend">Frontend</a> &bull;
  <a href="#docker">Docker</a> &bull;
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
  <img src="https://img.shields.io/badge/Azure%20AI-Evaluation-E83E8C.svg" alt="Azure AI Evaluation">
  <img src="https://img.shields.io/badge/FastAPI-SSE%20Streaming-009688.svg" alt="FastAPI SSE">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker">
  <img src="https://img.shields.io/badge/CI-Evaluation%20Gate-F5A623.svg" alt="CI Evaluation Gate">
</p>

---

## Deploy to Azure

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmsftse%2Fmicrosoft-agent-framework-geekacademy%2Fmain%2Fazuredeploy.json)

> Deploys an Azure AI Foundry project with a `gpt-4o` model deployment and Application Insights for tracing.

---

## Overview

This project demonstrates how to build a **multi-agent content creation pipeline** using the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) for Python. Three AI agents collaborate in sequence to research, write, and review technical articles — powered by Azure AI Foundry and connected to live data sources via MCP (Model Context Protocol) tools.

### What You'll Learn

- Creating AI agents with `AzureAIAgentClient`
- Connecting agents to external tools via **MCP** (Streamable HTTP and stdio)
- Orchestrating agents in a **sequential workflow** using `SequentialBuilder`
- Streaming agent outputs with real-time handoff visibility
- Exposing and consuming agents via the **A2A (Agent-to-Agent) protocol**
- **Evaluating AI outputs** with Azure AI Foundry built-in evaluators (Coherence, Fluency, Relevance)
- Serving agents as a **REST API with SSE streaming** using FastAPI
- Setting up **Azure Monitor tracing** for observability in AI Foundry

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │     Sequential Workflow      │
                    └─────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌─────────────┐       ┌──────────────┐       ┌──────────────┐
   │  Researcher  │       │    Writer     │       │   Reviewer   │
   │              │       │              │       │              │
   │  Gathers     │──────▶│  Transforms  │──────▶│  Polishes    │
   │  information │       │  into article│       │  final draft │
   └──────┬───────┘       └──────────────┘       └──────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐ ┌────────┐
│MS Learn│ │ GitHub │
│  MCP   │ │  MCP   │
│ (HTTP) │ │(stdio) │
└────────┘ └────────┘
```

| Agent | Role | MCP Tools |
|-------|------|-----------|
| **Researcher** | Gathers facts, docs, and code examples on the topic | Microsoft Learn, GitHub |
| **Writer** | Transforms the research brief into a developer-friendly article | None |
| **Reviewer** | Edits for accuracy, clarity, and structure; outputs the final version | None |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the GitHub MCP server via `npx`)
- **Azure CLI** — logged in (`az login`)
- **Azure AI Foundry project** with a deployed model (e.g., `gpt-4o`)
- **GitHub Personal Access Token** — [create one here](https://github.com/settings/tokens)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/msftse/microsoft-agent-framework-geekacademy.git
cd microsoft-agent-framework-geekacademy
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
# or using pyproject.toml
pip install .
```

Or install directly:

```bash
pip install "agent-framework[azure]" azure-identity azure-monitor-opentelemetry opentelemetry-sdk python-dotenv
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Required - Azure AI Foundry project endpoint
PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
MODEL_DEPLOYMENT_NAME=gpt-4o

# Required - GitHub MCP server
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Optional - Azure Monitor tracing (leave empty for console output)
APPLICATION_INSIGHTS_CONNECTION_STRING=
```

> **Finding your project endpoint:** In [Azure AI Foundry](https://ai.azure.com), open your project → Settings → Project endpoint.

### 4. Login to Azure

```bash
az login
```

### 5. Run the pipeline

```bash
python run.py
```

Or as a module:

```bash
python -m pipeline.main
```

You'll be prompted to enter a topic (or press Enter for the default). The pipeline will stream output from each agent in sequence:

```
[Researcher]:
<research brief with docs and code examples>
----------------------------------------
[Writer]:
<developer-friendly article>
----------------------------------------
[Reviewer]:
<final polished version>

============================================================
Pipeline complete!
```

---

## Project Structure

```
├── .env.example          # Environment variable template
├── .gitignore            # Protects .env and caches
├── .github/workflows/
│   └── evaluation.yml    # CI evaluation gate for PRs
├── Dockerfile            # Multi-stage Docker build (Python + Node.js)
├── docker-compose.yml    # One-command startup with .env
├── pyproject.toml        # Dependencies and project metadata
├── run.py                # Entry point — python run.py
├── pipeline/
│   ├── __init__.py
│   ├── config.py          # Loads and validates settings from .env
│   ├── tracing.py         # Azure Monitor or console tracing setup
│   ├── tools.py           # MCP tool factories (Learn HTTP + GitHub stdio)
│   ├── agents.py          # Agent definitions (Researcher, Writer, Reviewer)
│   ├── workflow.py        # SequentialBuilder pipeline
│   └── main.py            # Async entry point — wires everything together
├── a2a_demo/
│   ├── __init__.py
│   ├── server.py          # Exposes Reviewer agent as A2A server
│   └── client.py          # Consumes the remote agent via A2A protocol
├── evaluation/
│   ├── __init__.py
│   ├── dataset.jsonl      # 5-sample eval dataset (query + response pairs)
│   ├── run.py             # Runs Coherence, Fluency, Relevance evaluators
│   └── ci.py              # CI gate — exits non-zero if scores below threshold
├── api/
│   ├── __init__.py
│   └── server.py          # FastAPI server with SSE streaming endpoints
└── frontend/
    └── index.html         # Single-page chat UI (served at localhost:8000)
```

### Key Files Explained

| File | What It Does |
|------|-------------|
| `config.py` | Reads `.env`, validates required settings, returns a frozen `Settings` dataclass |
| `tracing.py` | Configures OpenTelemetry — Azure Monitor exporters when `APPLICATION_INSIGHTS_CONNECTION_STRING` is set, console output otherwise |
| `tools.py` | Creates two MCP tools: **Microsoft Learn** (Streamable HTTP) and **GitHub** (stdio via `npx`) |
| `agents.py` | Defines three agents using `AzureAIAgentClient.as_agent()` with role-specific system prompts |
| `workflow.py` | Chains agents into a sequential workflow using `SequentialBuilder` |
| `main.py` | Orchestrates startup: config → tracing → client → MCP tools → agents → workflow → stream output |

---

## Tracing & Observability

The pipeline supports two tracing modes:

### Azure Monitor (recommended)

Set `APPLICATION_INSIGHTS_CONNECTION_STRING` in your `.env`. Traces appear in the **Azure AI Foundry portal** under your project's tracing tab, showing:

- Full workflow span with latency
- Per-agent execution spans (Researcher, Writer, Reviewer)
- Chat completion calls to `gpt-4o`
- MCP tool invocations

### Console (local dev)

Leave `APPLICATION_INSIGHTS_CONNECTION_STRING` empty. Spans are printed to stdout for quick debugging.

---

## How It Works

1. **Config** — `load_settings()` reads `.env` and validates required values
2. **Tracing** — `setup_tracing()` configures OpenTelemetry with Azure Monitor or console exporters via `configure_otel_providers()`
3. **Client** — `AzureAIAgentClient` connects to Azure AI Foundry using `AzureCliCredential`
4. **MCP Tools** — Microsoft Learn (HTTP) and GitHub (stdio) servers start as async context managers
5. **Agents** — Three agents are created with `client.as_agent()`, each with role-specific instructions
6. **Workflow** — `SequentialBuilder` chains Researcher → Writer → Reviewer
7. **Streaming** — `workflow.run_stream()` yields events showing real-time agent handoffs and text output

---

## A2A Protocol Demo

The project also includes a standalone demo of the [Agent-to-Agent (A2A) protocol](https://github.com/google/A2A) — an open standard for inter-agent communication over HTTP/JSON-RPC. The Microsoft Agent Framework supports A2A natively, allowing any agent to be exposed as a remote service or consumed as a remote participant.

### How It Works

```
Terminal 1 (Server)                    Terminal 2 (Client)
┌──────────────────────┐              ┌──────────────────────┐
│  Reviewer Agent      │    A2A       │  A2AAgent            │
│  (Azure AI Foundry)  │◀──JSON-RPC──│  (framework client)  │
│                      │              │                      │
│  Exposed via         │   HTTP       │  Calls remote agent  │
│  A2AStarletteApp     │──────────── ▶│  like a local one    │
│  on localhost:9000   │              │                      │
└──────────────────────┘              └──────────────────────┘
```

**Server** (`a2a_demo/server.py`):
- Creates a Reviewer agent using `AzureAIAgentClient`
- Wraps it in an `AgentExecutor` that bridges agent-framework to the A2A protocol
- Serves it via `A2AStarletteApplication` + `uvicorn` on `localhost:9000`
- Publishes an **Agent Card** at `/.well-known/agent-card.json` describing its capabilities

**Client** (`a2a_demo/client.py`):
- Creates an `A2AAgent(url="http://localhost:9000")` — same interface as any local agent
- Sends a draft article for review over the A2A protocol
- Receives the polished article back

### Run the Demo

**Terminal 1** — Start the A2A server:
```bash
python -m a2a_demo.server
```

**Terminal 2** — Run the A2A client:
```bash
python -m a2a_demo.client
```

> The client sends a sample draft article with intentional issues. The remote Reviewer agent reviews and polishes it, returning the result over A2A.

### Why A2A Matters

- **Interoperability** — Agents built with different frameworks can communicate via the standard A2A protocol
- **Remote execution** — Agents can run on separate machines/services and collaborate over HTTP
- **Discovery** — Agent Cards let clients discover agent capabilities automatically
- **Same interface** — `A2AAgent` implements the same protocol as local agents, so it plugs into workflows and tools seamlessly

---

## Evaluation

The project includes an evaluation suite that measures the quality of pipeline outputs using [Azure AI Foundry built-in evaluators](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/evaluate-generative-ai-app). This gives you quantitative scores to validate that your agents produce high-quality content.

### Evaluators

| Evaluator | What It Measures | Scale |
|-----------|-----------------|-------|
| **Coherence** | Logical flow and readability of the article | 1-5 |
| **Fluency** | Language quality — grammar, vocabulary, sentence structure | 1-5 |
| **Relevance** | How well the response addresses the original query | 1-5 |

### Dataset

The evaluation runs against `evaluation/dataset.jsonl` — a JSONL file where each line contains:

```json
{"query": "Write a technical article about ...", "response": "# Article Title\n\n..."}
```

The included dataset has 5 samples covering Azure Functions, AKS, Cosmos DB, Microsoft Agent Framework, and GitHub Actions CI/CD. The last sample is intentionally shorter to demonstrate score variation.

### Run the Evaluation

```bash
python -m evaluation.run
```

Example output:

```
============================================================
Azure AI Foundry Evaluation
============================================================

Endpoint:   https://<your-resource>.services.ai.azure.com
Project:    https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
Model:      gpt-4o
Dataset:    evaluation/dataset.jsonl
Samples:    5

Running evaluators: Coherence, Fluency, Relevance
────────────────────────────────────────────────────────────

============================================================
RESULTS SUMMARY
============================================================

  coherence.coherence                      4.60
  fluency.fluency                          4.20
  relevance.relevance                      4.80

────────────────────────────────────────────────────────────
PER-SAMPLE SCORES
────────────────────────────────────────────────────────────

  [1] Write a technical article about Azure Functions serverle...
      Coherence=5  Fluency=5  Relevance=5

  [2] Write a technical article about Azure Kubernetes Service...
      Coherence=5  Fluency=4  Relevance=5

  ...

============================================================
Evaluation complete!

View in Foundry: https://ai.azure.com/resource/build/evaluation/<run-id>?wsid=...
```

> Results are automatically logged to the **Evaluation** tab in Azure AI Foundry. Click the `View in Foundry` link to see detailed metrics, per-sample scores, and visualizations in the portal.

---

## API Server

The project includes a **FastAPI server** that exposes the pipeline and individual agents as REST API endpoints with **Server-Sent Events (SSE)** streaming. This is the foundation for building a frontend UI on top of the agents.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — returns available agents |
| `POST` | `/api/pipeline` | Run the full Researcher -> Writer -> Reviewer pipeline |
| `POST` | `/api/agents/researcher` | Run the Researcher agent individually |
| `POST` | `/api/agents/writer` | Run the Writer agent individually |
| `POST` | `/api/agents/reviewer` | Run the Reviewer agent individually |

### Start the Server

```bash
python3 -m api.server
```

The server starts on `http://localhost:8000`. Agents, MCP tools, and the pipeline are initialized once at startup.

### SSE Event Format

All streaming endpoints return Server-Sent Events with three event types:

```
event: agent
data: {"agent": "Researcher"}     # Agent started working

event: text
data: {"agent": "Researcher", "text": "Azure Functions is..."}  # Text token

event: done
data: {"status": "complete"}      # Stream finished
```

### Example Requests

**Health check:**
```bash
curl http://localhost:8000/api/health
```

**Run the full pipeline:**
```bash
curl -N -X POST http://localhost:8000/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{"topic": "Azure Container Apps"}'
```

**Run a single agent:**
```bash
curl -N -X POST http://localhost:8000/api/agents/writer \
  -H "Content-Type: application/json" \
  -d '{"message": "Write a 3-sentence intro about Azure Functions"}'
```

> **Tip:** The `-N` flag disables curl's output buffering so you see SSE events in real time.

### Frontend Integration

The SSE format is designed for easy frontend consumption using the standard `EventSource` API or `fetch` with streaming:

```javascript
const response = await fetch("/api/pipeline", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ topic: "Azure Functions" }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  // Parse SSE events and update UI
  console.log(decoder.decode(value));
}
```

---

## Frontend

The project includes a **single-page chat UI** built as one self-contained HTML file — no build tools or npm required. It's served automatically by the FastAPI server.

### Features

- **Pipeline mode** — enter a topic and watch Researcher, Writer, and Reviewer work sequentially with live agent handoff indicators
- **Single Agent mode** — pick an agent (Researcher, Writer, or Reviewer) and chat with it directly
- Real-time SSE streaming with color-coded agent labels
- Dark theme, responsive layout

### Usage

Start the API server and open the browser:

```bash
python3 -m api.server
# Open http://localhost:8000 in your browser
```

The frontend is served at the root (`/`). Switch between Pipeline and Single Agent modes using the toggle in the header.

---

## Docker

Run the entire application in a container — no local Python or Node.js required.

### Prerequisites

Add service principal credentials to your `.env` file (since `az login` is not available inside Docker):

```env
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Run with Docker Compose

```bash
docker compose up --build
```

The app starts on `http://localhost:8000` with the frontend, API, and all agents ready.

### Run with Docker directly

```bash
docker build -t maf-poc .
docker run -p 8000:8000 --env-file .env maf-poc
```

---

## CI — Evaluation Gate

Every pull request to `main` automatically runs the AI quality evaluation suite via GitHub Actions. The PR is blocked if any score falls below the threshold.

### How It Works

1. PR is opened against `main`
2. GitHub Action installs dependencies and runs `python -m evaluation.ci --threshold 4.0`
3. Coherence, Fluency, and Relevance evaluators score the dataset against Azure AI Foundry
4. If any metric scores below **4.0/5.0**, the check fails and the PR cannot be merged
5. Results are posted as a summary on the PR and uploaded as an artifact

### Required GitHub Secrets

Configure these in your repo under **Settings > Secrets and variables > Actions**:

| Secret | Description |
|--------|-------------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name (e.g., `gpt-4o`) |
| `AZURE_TENANT_ID` | Service principal tenant ID |
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |

### Run Locally

```bash
python -m evaluation.ci --threshold 4.0
```

---

## Technologies

| Technology | Usage |
|-----------|-------|
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Agent creation, workflows, MCP integration |
| [Azure AI Foundry](https://ai.azure.com) | LLM hosting (gpt-4o), tracing, project management |
| [Model Context Protocol (MCP)](https://modelcontextprotocol.io) | Tool connectivity — Microsoft Learn & GitHub |
| [Agent-to-Agent Protocol (A2A)](https://github.com/google/A2A) | Inter-agent communication over HTTP/JSON-RPC |
| [Azure Monitor / OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/) | Distributed tracing and observability |
| [Azure AI Evaluation](https://learn.microsoft.com/en-us/python/api/azure-ai-evaluation/) | Quality scoring — Coherence, Fluency, Relevance evaluators |
| [Azure Identity](https://learn.microsoft.com/en-us/python/api/azure-identity/) | Authentication via Azure CLI credential |
| [FastAPI](https://fastapi.tiangolo.com) | REST API server with SSE streaming endpoints |
| [SSE-Starlette](https://github.com/sysid/sse-starlette) | Server-Sent Events support for real-time streaming |

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `ModuleNotFoundError: No module named 'pipeline'` | Run from the project root: `python run.py` or `python -m pipeline.main` |
| `EnvironmentError: PROJECT_ENDPOINT is required` | Copy `.env.example` to `.env` and fill in your Azure AI Foundry project endpoint |
| `401 Unauthorized` | Run `az login` to refresh your Azure CLI credential |
| GitHub MCP server hangs | Ensure Node.js 18+ is installed and `npx` is available in your PATH |
| Traces not appearing in AI Foundry | Verify `APPLICATION_INSIGHTS_CONNECTION_STRING` is correct; traces may take 1-2 minutes to appear |

---

## License

MIT

---

<p align="center">
  Built for <strong>Geek Academy</strong> — Become an AI Architect with AI-Powered Tools from Microsoft and GitHub
</p>
