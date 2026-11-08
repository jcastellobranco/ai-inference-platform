# ATLAS reliability starter

## SLIs and proposed SLOs (learning targets, not measured promises)

- API availability SLI: successful eligible HTTP requests / all eligible requests. Proposed 30-day SLO: 99.5%.
- API latency SLI: share of eligible requests completed under 500 ms. Proposed 30-day SLO: 95%.
- Worker completion SLI: jobs reaching terminal success within 5 minutes / eligible accepted jobs. Proposed SLO: 95%. Exclude intentionally long-running tasks by job class.
- Tenant isolation: zero known cross-tenant data disclosures; treat any violation as an incident, not a numerical error budget.

## Operational drills

1. Break a database connection and verify readiness and API error handling.
2. Trigger a worker crash mid-job; verify lease expiry and retry behavior without duplicate external side effects.
3. Deploy a deliberately broken image to a disposable environment; roll back to the last healthy digest.
4. Observe latency, failures and queue age; record incident timeline and recovery time.
5. Verify that logs do not include bearer tokens, prompts or tenant-private data.

## Known gaps

The request middleware supplies logs and duration but does not provide distributed tracing, persisted metrics, alerting, readiness probes, dashboards or rollback automation. Those require deployment infrastructure and telemetry backends. Do not claim SLO compliance until real SLIs are collected.
