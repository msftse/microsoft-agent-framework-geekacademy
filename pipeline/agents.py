"""Agent definitions — Researcher, Writer, Reviewer.

Each agent is created via AzureAIProjectAgentProvider.create_agent(), which
**eagerly** registers the agent as a persistent resource in Azure AI Foundry.
The agents are visible in the Foundry portal immediately after startup.

When memory is enabled, agents are created with a memory_search tool that
allows them to recall relevant information from previous interactions.
"""

from __future__ import annotations

from agent_framework.azure import AzureAIProjectAgentProvider

from prompts import load_prompt


def _memory_tool(memory_store_name: str, scope: str = "pipeline_user") -> dict:
    """Build the memory_search tool definition dict."""
    return {
        "type": "memory_search",
        "memory_store_name": memory_store_name,
        "scope": scope,
        "update_delay": 2,
    }


async def create_researcher(
    provider: AzureAIProjectAgentProvider,
    tools: list | None = None,
    model: str | None = None,
    memory_store_name: str | None = None,
):
    """Researcher agent — uses MCP tools to gather information.

    MCP tools cannot be passed directly to provider.create_agent() because
    they are runtime-only (not stored on the Azure service).  We create the
    agent without them, then attach MCP tools to the local Agent wrapper.
    """
    agent_tools = []
    if memory_store_name:
        agent_tools.append(_memory_tool(memory_store_name))

    agent = await provider.create_agent(
        name="Researcher",
        model=model,
        instructions=load_prompt("researcher"),
        tools=agent_tools or None,
    )
    # Attach MCP tools to the local Agent wrapper for runtime use
    if tools:
        from agent_framework._mcp import MCPTool

        agent.mcp_tools = [t for t in tools if isinstance(t, MCPTool)]
    return agent


async def create_writer(
    provider: AzureAIProjectAgentProvider,
    model: str | None = None,
    memory_store_name: str | None = None,
):
    """Writer agent — transforms research into a developer article.

    Registered in AI Foundry as "Writer".
    """
    agent_tools = []
    if memory_store_name:
        agent_tools.append(_memory_tool(memory_store_name))

    return await provider.create_agent(
        name="Writer",
        model=model,
        instructions=load_prompt("writer"),
        tools=agent_tools or None,
    )


async def create_reviewer(
    provider: AzureAIProjectAgentProvider,
    model: str | None = None,
    memory_store_name: str | None = None,
):
    """Reviewer agent — polishes the final article.

    Registered in AI Foundry as "Reviewer".
    """
    agent_tools = []
    if memory_store_name:
        agent_tools.append(_memory_tool(memory_store_name))

    return await provider.create_agent(
        name="Reviewer",
        model=model,
        instructions=load_prompt("reviewer"),
        tools=agent_tools or None,
    )
