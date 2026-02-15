"""Workflow builder — sequential pipeline: Researcher -> Writer -> Reviewer."""

from __future__ import annotations

from agent_framework.orchestrations import SequentialBuilder


def build_pipeline(researcher, writer, reviewer):
    """Build a sequential multi-agent workflow.

    Uses the new AI Foundry-compatible SequentialBuilder from
    agent_framework.orchestrations (replaces the old _workflows internal module).
    """
    return SequentialBuilder(participants=[researcher, writer, reviewer]).build()
