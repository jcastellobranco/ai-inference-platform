"""Verify the four Grafana-managed ATLAS alert rules are provisioned.

Read-only request to loopback Grafana. Credentials come from the local,
untracked .env and are never printed or passed as command-line arguments.
"""
from __future__ import annotations

from base64 import b64encode
from json import load
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "atlas-worker-queue-backlog",
    "atlas-worker-failure-rate",
    "atlas-rag-search-p95",
    "atlas-target-down",
}
URL = "http://127.0.0.1:3000/api/v1/provisioning/alert-rules"


def local_grafana_credentials(path: Path = ROOT / ".env") -> tuple[str, str]:
    """Parse only local Grafana admin keys; do not interpolate shell expressions."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key in {"GRAFANA_ADMIN_USER", "GRAFANA_ADMIN_PASSWORD"}:
            values[key] = value.strip().strip('"').strip("'")
    return values.get("GRAFANA_ADMIN_USER") or "admin", values.get("GRAFANA_ADMIN_PASSWORD", "")


def verify_rules(rules: list[dict]) -> tuple[bool, str]:
    actual = {rule.get("uid"): rule for rule in rules}
    missing = EXPECTED - actual.keys()
    paused = {uid for uid in EXPECTED & actual.keys() if actual[uid].get("isPaused")}
    if missing or paused:
        return False, f"Missing={sorted(missing)} paused={sorted(paused)}"
    return True, "All four ATLAS alert rules are provisioned and enabled"


def main() -> int:
    try:
        user, password = local_grafana_credentials()
        if not password:
            print("Missing local Grafana password; run make init")
            return 1
        auth = b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        request = Request(URL, headers={"Authorization": f"Basic {auth}"})
        with urlopen(request, timeout=10) as response:
            rules = load(response)
        ok, message = verify_rules(rules)
        print(("SUCCESS: " if ok else "FAILED: ") + message)
        return 0 if ok else 1
    except FileNotFoundError:
        print("Missing .env; run make init")
    except HTTPError as exc:
        print(f"Grafana API returned HTTP {exc.code}; check Grafana admin credentials and provisioning")
    except (URLError, TimeoutError, OSError, ValueError):
        print("Cannot query local Grafana alert rules; check make ps-observability")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
