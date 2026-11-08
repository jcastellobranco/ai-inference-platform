# ATLAS platform engineering learning track

This repository demonstrates four practices. It is a portfolio learning platform, **not** a production-ready internal developer platform.

## 1. Container engineering and integration testing

- Multi-stage Python and frontend images.
- Root `.dockerignore` reduces build context.
- PostgreSQL 17 Testcontainers suite checks migrations, RLS, tenant separation and transaction-local context.
- Local: `python -m pip install -e '.[dev]' && python -m pytest tests -q`.
- Docker daemon must be available for integration tests.

## 2. CI and image quality

- `.github/workflows/ci.yml` runs Python tests, including Testcontainers.
- `.github/workflows/container-quality.yml` builds backend and frontend images and scans for unfixed critical CVEs.
- No AWS or ECR push is needed for this exercise.
- For production, pin GitHub Actions to full commit SHAs and establish vulnerability exceptions and remediation SLAs.

## 3. Golden path and developer experience

- Reusable sample service under `platform/golden-path/fastapi-service/`.
- Standard endpoint, container, tests, CI example and documented usage.
- This is a **starter template**, not a fully automated self-service catalog; Backstage/Port are optional future extensions.
- Define ownership, lifecycle, secret handling and tenant isolation before adopting organization-wide.

## 4. Reliability and observability

- HTTP request telemetry middleware emits request ID, status, route template and duration without request body or authorization headers.
- Liveness endpoint exists at `/health/live`.
- `docs/RELIABILITY.md` defines starter SLIs, SLOs and rollback exercises.
- Full OpenTelemetry traces, collector, Prometheus metrics, dashboards and alert delivery are **not implemented**; they require a runtime backend and validation.

## References

- CNCF Platform Engineering White Paper: https://tag-app-delivery.cncf.io/whitepapers/platform-eng/
- Google SRE Workbook: https://sre.google/workbook/table-of-contents/
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- Testcontainers Python: https://testcontainers-python.readthedocs.io/
