"""OpenTelemetry tracing. Exports via OTLP/HTTP when COS_OTEL_EXPORTER_OTLP_ENDPOINT is set."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import Settings

_configured = False


def configure_tracing(settings: Settings) -> None:
    global _configured
    if _configured:
        return
    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": settings.service_name, "deployment.environment": settings.environment.value}
        )
    )
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces"))
        )
    trace.set_tracer_provider(provider)
    _configured = True


def tracer() -> trace.Tracer:
    return trace.get_tracer("commerce-os")


def current_trace_id() -> str | None:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else None
