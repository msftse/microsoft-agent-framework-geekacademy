"""Agent definitions — Researcher, Writer, Reviewer.

Each agent is created via AzureAIAgentsProvider.create_agent(), which
**eagerly** registers the agent as a persistent resource in Azure AI Foundry.
The agents are visible in the Foundry portal immediately after startup.
"""

from __future__ import annotations

from agent_framework.azure import AzureAIAgentsProvider

from prompts import load_prompt


async def create_researcher(
    provider: AzureAIAgentsProvider, tools: list | None = None, model: str | None = None
):
    """Researcher agent — uses MCP tools to gather information.

    MCP tools cannot be passed directly to provider.create_agent() because
    they are runtime-only (not stored on the Azure service).  We create the
    agent without them, then attach MCP tools to the local Agent wrapper.
    """
    agent = await provider.create_agent(
        name="Researcher",
        model=model,
        instructions=load_prompt("researcher"),
    )
    # Attach MCP tools to the local Agent wrapper for runtime use
    if tools:
        from agent_framework._mcp import MCPTool

        agent.mcp_tools = [t for t in tools if isinstance(t, MCPTool)]
    return agent


async def create_writer(provider: AzureAIAgentsProvider, model: str | None = None):
    """Writer agent — transforms research into a developer article.

    Registered in AI Foundry as "Writer".
    """
    return await provider.create_agent(
        name="Writer",
        model=model,
        instructions=load_prompt("writer"),
    )


async def create_reviewer(provider: AzureAIAgentsProvider, model: str | None = None):
    """Reviewer agent — polishes the final article.

    Registered in AI Foundry as "Reviewer".
    """
    return await provider.create_agent(
        name="Reviewer",
        model=model,
        instructions=load_prompt("reviewer"),
    )
