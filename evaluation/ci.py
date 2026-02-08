"""CI evaluation gate — runs evaluators and fails if scores are below threshold.

Used by GitHub Actions to enforce quality on PRs to main.

Run:  python -m evaluation.ci [--threshold 4.0]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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
DEFAULT_THRESHOLD = 4.0


def get_config() -> tuple[dict, str]:
    """Build model configuration and project endpoint from environment."""
    load_dotenv()

    project_endpoint = os.environ.get("PROJECT_ENDPOINT", "")
    if not project_endpoint:
        raise EnvironmentError("PROJECT_ENDPOINT is required. See .env.example")

    azure_endpoint = (
        project_endpoint.split("/api/projects/")[0]
        if "/api/projects/" in project_endpoint
        else project_endpoint
    )
    deployment = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    model_config = {
        "azure_endpoint": azure_endpoint,
        "azure_deployment": deployment,
        "api_version": "2025-04-01-preview",
    }
    return model_config, project_endpoint


def run_evaluation(threshold: float) -> bool:
    """Run evaluators and return True if all scores meet the threshold."""
    model_config, project_endpoint = get_config()
    credential = DefaultAzureCredential()

    print(f"Endpoint:    {model_config['azure_endpoint']}")
    print(f"Model:       {model_config['azure_deployment']}")
    print(f"Threshold:   {threshold}/5.0")
    print(f"Dataset:     {DATASET_PATH}")
    print()

    coherence = CoherenceEvaluator(model_config=model_config, credential=credential)
    fluency = FluencyEvaluator(model_config=model_config, credential=credential)
    relevance = RelevanceEvaluator(model_config=model_config, credential=credential)

    result = evaluate(
        data=str(DATASET_PATH),
        evaluation_name="CI Evaluation Gate",
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
        azure_ai_project=project_endpoint,
        output_path=str(Path(__file__).parent / "results.json"),
    )

    metrics = result.get("metrics", {})
    passed = True

    print("=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)

    for name, value in sorted(metrics.items()):
        if not isinstance(value, (int, float)):
            continue
        status = "PASS" if value >= threshold else "FAIL"
        if value < threshold:
            passed = False
        print(f"  {name:40s} {value:.2f}  [{status}]")

    print("=" * 50)

    # Write GitHub Actions summary if running in CI
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write("## Evaluation Results\n\n")
            f.write(f"**Threshold:** {threshold}/5.0\n\n")
            f.write("| Metric | Score | Status |\n")
            f.write("|--------|-------|--------|\n")
            for name, value in sorted(metrics.items()):
                if not isinstance(value, (int, float)):
                    continue
                status = "PASS" if value >= threshold else "FAIL"
                f.write(f"| {name} | {value:.2f} | {status} |\n")
            f.write(f"\n**Overall: {'PASSED' if passed else 'FAILED'}**\n")

    if passed:
        print("\nAll scores meet the threshold. PASSED.")
    else:
        print(f"\nOne or more scores below {threshold}. FAILED.")

    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="CI evaluation gate")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum acceptable score (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    passed = run_evaluation(args.threshold)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
