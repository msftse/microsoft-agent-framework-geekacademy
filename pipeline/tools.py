"""MCP tool factories — Microsoft Learn (HTTP) and GitHub (stdio)."""

from __future__ import annotations

from agent_framework import MCPStreamableHTTPTool, MCPStdioTool


def create_learn_tool() -> MCPStreamableHTTPTool:
    """Microsoft Learn documentation search via Streamable HTTP MCP."""
    return MCPStreamableHTTPTool(
        name="Microsoft Learn",
        url="https://learn.microsoft.com/api/mcp",
    )


def create_github_tool(token: str) -> MCPStdioTool:
    """GitHub repository access via stdio MCP server."""
    return MCPStdioTool(
        name="GitHub",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
        load_prompts=False,  # GitHub MCP server doesn't support prompts
    )
