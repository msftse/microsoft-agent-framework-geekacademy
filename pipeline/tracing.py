"""Tracing setup — Azure Monitor when available, console fallback for local dev."""

from __future__ import annotations

import os

from pipeline.config import Settings


def setup_tracing(settings: Settings) -> None:
    """Configure OpenTelemetry tracing for the agent pipeline."""
    from agent_framework.observability import configure_otel_providers

    if settings.app_insights_connection_string:
        try:
            # Production: export traces + logs + metrics to Azure Monitor / AI Foundry
            from azure.monitor.opentelemetry.exporter import (
                AzureMonitorLogExporter,
                AzureMonitorMetricExporter,
                AzureMonitorTraceExporter,
            )

            cs = settings.app_insights_connection_string
            configure_otel_providers(
                exporters=[
                    AzureMonitorTraceExporter(connection_string=cs),
                    AzureMonitorLogExporter(connection_string=cs),
                    AzureMonitorMetricExporter(connection_string=cs),
                ],
            )
            print(
                "[tracing] Azure Monitor configured — traces visible in AI Foundry portal"
            )
            return
        except Exception as exc:
            print(
                f"[tracing] Azure Monitor setup failed ({exc}), falling back to console"
            )

    # Local dev / fallback: print spans to console
    os.environ.setdefault("ENABLE_CONSOLE_EXPORTERS", "true")
    try:
        configure_otel_providers()
    except Exception:
        pass  # tracing is optional — don't block the app
    print(
        "[tracing] Console exporter enabled — set APPLICATION_INSIGHTS_CONNECTION_STRING for Azure Monitor"
    )
