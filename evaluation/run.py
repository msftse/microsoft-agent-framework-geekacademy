"""Evaluate content pipeline outputs using Azure AI Foundry built-in evaluators.

Runs Coherence, Fluency, and Relevance evaluators against a sample dataset
and prints a summary of scores.

Run:  python -m evaluation.run
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import (
    evaluate,
    CoherenceEvaluator,
    FluencyEvaluator,
    RelevanceEvaluator,
)
from dotenv import load_dotenv

DATASET_PATH = Path(__file__).parent / "dataset.jsonl"


def get_model_config() -> dict:
    """Build the model configuration from environment variables."""
    load_dotenv()

    project_endpoint = os.environ.get("PROJECT_ENDPOINT", "")
    if not project_endpoint:
        raise EnvironmentError("PROJECT_ENDPOINT is required. See .env.example")

    # Evaluators need the resource-level endpoint (without /api/projects/...)
    azure_endpoint = (
        project_endpoint.split("/api/projects/")[0]
        if "/api/projects/" in project_endpoint
        else project_endpoint
    )

    deployment = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    return {
        "azure_endpoint": azure_endpoint,
        "azure_deployment": deployment,
        "api_version": "2025-04-01-preview",
    }


def main() -> None:
    print(f"\n{'=' * 60}")
    print("Azure AI Foundry Evaluation")
    print(f"{'=' * 60}\n")

    model_config = get_model_config()
    credential = DefaultAzureCredential()

    print(f"Endpoint:   {model_config['azure_endpoint']}")
    print(f"Model:      {model_config['azure_deployment']}")
    print(f"Dataset:    {DATASET_PATH}")

    # Count rows
    with open(DATASET_PATH) as f:
        row_count = sum(1 for _ in f)
    print(f"Samples:    {row_count}")

    # Initialize evaluators (use credential for token-based auth)
    coherence = CoherenceEvaluator(model_config=model_config, credential=credential)
    fluency = FluencyEvaluator(model_config=model_config, credential=credential)
    relevance = RelevanceEvaluator(model_config=model_config, credential=credential)

    print(f"\nRunning evaluators: Coherence, Fluency, Relevance")
    print(f"{'─' * 60}\n")

    # Run evaluation
    result = evaluate(
        data=str(DATASET_PATH),
        evaluators={
            "coherence": coherence,
            "fluency": fluency,
            "relevance": relevance,
        },
        evaluator_config={
            "coherence": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}",
                },
            },
            "fluency": {
                "column_mapping": {
                    "response": "${data.response}",
                },
            },
            "relevance": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}",
                },
            },
        },
    )

    # Print summary metrics
    print(f"\n{'=' * 60}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 60}\n")

    metrics = result.get("metrics", {})
    for name, value in sorted(metrics.items()):
        if isinstance(value, float):
            print(f"  {name:40s} {value:.2f}")
        else:
            print(f"  {name:40s} {value}")

    # Print per-row scores
    rows = result.get("rows", [])
    if rows:
        print(f"\n{'─' * 60}")
        print("PER-SAMPLE SCORES")
        print(f"{'─' * 60}\n")

        for i, row in enumerate(rows):
            query = row.get("inputs.query", "")
            # Truncate long queries
            query_short = query[:60] + "..." if len(query) > 60 else query
            coh = row.get("outputs.coherence.coherence", "N/A")
            flu = row.get("outputs.fluency.fluency", "N/A")
            rel = row.get("outputs.relevance.relevance", "N/A")
            print(f"  [{i + 1}] {query_short}")
            print(f"      Coherence={coh}  Fluency={flu}  Relevance={rel}\n")

    print(f"{'=' * 60}")
    print("Evaluation complete!")

    # Optionally save full results
    output_path = Path(__file__).parent / "results.json"
    with open(output_path, "w") as f:
        json.dump(
            {"metrics": metrics, "rows": rows},
            f,
            indent=2,
            default=str,
        )
    print(f"Full results saved to: {output_path}")


if __name__ == "__main__":
    main()
