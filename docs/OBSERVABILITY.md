# ATLAS local observability

This is a **local-only** learning stack: OpenTelemetry traces -> Collector -> Tempo -> Grafana, plus Prometheus metrics scraped from FastAPI.

## Start

Set `JWT_SECRET` (32+ random characters) and `GRAFANA_ADMIN_PASSWORD` in your environment or `.env`. Then, from the repository root:

```bash
docker compose -f docker-compose.fullstack.yml -f observability/docker-compose.observability.yml up --build -d
```

Open Grafana at http://localhost:3000 (user `admin`, password from `GRAFANA_ADMIN_PASSWORD`) and Prometheus at http://localhost:9090.

Try `curl http://localhost:8080/health/live` if your frontend proxies that path, or `docker compose -f docker-compose.fullstack.yml -f observability/docker-compose.observability.yml exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health/live').read())"`.

Prometheus queries: `sum(rate(atlas_http_requests_total[5m]))`, `sum by (status) (rate(atlas_http_requests_total[5m]))`, `histogram_quantile(0.95, sum by (le) (rate(atlas_http_request_duration_seconds_bucket[5m])))`.

In Grafana Explore, select Tempo to view traces, and Prometheus to query metrics. Grafana/Prometheus ports are bound to loopback only. No AWS needed.

**Limitations:** API request metrics and API/SQL traces are implemented. Worker instrumentation, dashboards, alert routing and cross-service propagation to RAG/agent/evaluation remain future work. For production use TLS, auth, restricted networks, sampling and retention planning; never expose the metrics endpoint publicly without network controls.
