"""Prompt loader — reads prompt text files from the prompts/ directory."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str, **kwargs: str) -> str:
    """Load a prompt file by name (without extension) and optionally format it.

    Args:
        name: Filename without the .txt extension (e.g. "researcher").
        **kwargs: Substitution variables for ``str.format()``.

    Returns:
        The prompt text, optionally with variables substituted.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    text = path.read_text(encoding="utf-8").strip()
    if kwargs:
        text = text.format(**kwargs)
    return text
