"""Workflow builder — sequential pipeline: Researcher -> Writer -> Reviewer."""

from __future__ import annotations

from agent_framework._workflows import SequentialBuilder
from agent_framework._workflows._workflow import Workflow


def build_pipeline(researcher, writer, reviewer) -> Workflow:
    """Build a sequential multi-agent workflow."""
    return SequentialBuilder().participants([researcher, writer, reviewer]).build()
