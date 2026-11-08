# Golden path: minimal FastAPI service

A copyable starting point for a small service. Replace the service name and add authentication, authorization, persistence and deployment settings appropriate to your workload.

```bash
cd platform/golden-path/fastapi-service
docker build -t atlas-starter .
docker run --rm -p 8000:8000 atlas-starter
curl http://localhost:8000/health/live
```

Run unit tests with `pip install -r requirements-dev.txt && pytest -q`. The starter is intentionally independent of Terraform and AWS. For services with PostgreSQL, adapt the Testcontainers integration tests from the main application.
