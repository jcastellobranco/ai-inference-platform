"""Optional OpenTelemetry tracing and Prometheus metrics for ATLAS.

No request payload, URL query string, JWT, tenant ID or prompt is added as a label.
"""
import os

from prometheus_client import Counter, Histogram, make_asgi_app
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

REQUESTS = Counter("atlas_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("atlas_http_request_duration_seconds", "HTTP request duration", ["method", "route"])
metrics_app = make_asgi_app()


def configure_telemetry(app):
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    provider = TracerProvider(resource=Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "atlas-api"),
    }))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health/live,metrics")
    from .db import engine
    SQLAlchemyInstrumentor().instrument(engine=engine)
