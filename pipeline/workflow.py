"""Workflow builder — sequential pipeline: Researcher -> Writer -> Reviewer."""

from __future__ import annotations

from agent_framework.orchestrations import SequentialBuilder
from agent_framework import AgentResponseUpdate, WorkflowBuilder


def build_pipeline(researcher, writer, reviewer):
    """Build a sequential multi-agent workflow.

    Uses the new AI Foundry-compatible SequentialBuilder from
    agent_framework.orchestrations (replaces the old _workflows internal module).
    """
    return (
        WorkflowBuilder(start_executor=researcher)
        .add_edge(researcher, writer)
        .add_edge(writer, reviewer)
        .build()
    )
