"""Agent definitions — Researcher, Writer, Reviewer."""

from __future__ import annotations

from agent_framework.azure import AzureAIAgentClient


RESEARCHER_INSTRUCTIONS = """\
You are a senior technical researcher. Your job is to gather comprehensive, \
accurate information on the given topic using the available MCP tools.

Use "Microsoft Learn" to find official Microsoft documentation and best practices.
Use "GitHub" to find real code examples and repository details.

Output a structured research brief with: key concepts, official references, \
and relevant code snippets. Be thorough but concise.\
"""

WRITER_INSTRUCTIONS = """\
You are a technical content writer for a developer audience. \
You receive a research brief and transform it into a clear, engaging article.

Guidelines:
- Use a professional but approachable tone
- Include code examples where appropriate
- Structure with clear headings and bullet points
- Keep it practical — developers want to build, not just read\
"""

REVIEWER_INSTRUCTIONS = """\
You are a senior technical editor. Review the draft article for:
- Technical accuracy and completeness
- Clarity and readability for developers
- Code example correctness
- Logical structure and flow

Output the final polished version of the article, fixing any issues found.\
"""


def create_researcher(client: AzureAIAgentClient, tools: list) -> object:
    """Researcher agent — uses MCP tools to gather information."""
    return client.as_agent(
        name="Researcher",
        instructions=RESEARCHER_INSTRUCTIONS,
        tools=tools,
    )


def create_writer(client: AzureAIAgentClient) -> object:
    """Writer agent — transforms research into a developer article."""
    return client.as_agent(
        name="Writer",
        instructions=WRITER_INSTRUCTIONS,
    )


def create_reviewer(client: AzureAIAgentClient) -> object:
    """Reviewer agent — polishes the final article."""
    return client.as_agent(
        name="Reviewer",
        instructions=REVIEWER_INSTRUCTIONS,
    )
