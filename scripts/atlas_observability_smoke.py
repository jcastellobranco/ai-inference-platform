"""Read-only smoke check for local ATLAS Prometheus and Grafana.

No credentials, cloud calls, or Docker socket access. Run after make up-observability.
"""
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

EXPECTED = {"atlas-api", "atlas-evaluation", "atlas-rag", "atlas-worker"}


def get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        return json.load(response)


def check() -> tuple[bool, str]:
    try:
        grafana = get_json("http://127.0.0.1:3000/api/health")
        targets = get_json("http://127.0.0.1:9090/api/v1/targets")
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return False, f"UI not ready: {type(exc).__name__}"
    if grafana.get("database") != "ok":
        return False, "Grafana database not ready"
    active = targets.get("data", {}).get("activeTargets", [])
    status = {target.get("labels", {}).get("job"): target.get("health")
              for target in active}
    missing = EXPECTED - status.keys()
    down = {job: status.get(job) for job in EXPECTED if status.get(job) != "up"}
    if missing or down:
        return False, f"Prometheus targets missing={sorted(missing)} not_up={down}"
    return True, "Grafana healthy; Prometheus API/evaluation/RAG/worker targets UP"


def main() -> int:
    for attempt in range(12):
        ok, message = check()
        if ok:
            print("SUCCESS:", message)
            return 0
        if attempt < 11:
            time.sleep(5)
    print("FAILED:", message, file=sys.stderr)
    print("Inspect make ps-observability and make logs-observability", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
