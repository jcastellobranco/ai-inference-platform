"""Offline tests for Grafana alert smoke verification."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "atlas_alerts_smoke", ROOT / "scripts/atlas_alerts_smoke.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AlertSmokeTests(unittest.TestCase):
    def test_all_rules_present_and_active(self):
        rules = [{"uid": uid, "isPaused": False} for uid in module.EXPECTED]
        self.assertTrue(module.verify_rules(rules)[0])

    def test_missing_and_paused_are_reported(self):
        rules = [{"uid": "atlas-worker-queue-backlog", "isPaused": True}]
        ok, message = module.verify_rules(rules)
        self.assertFalse(ok)
        self.assertIn("atlas-worker-queue-backlog", message)
        self.assertIn("atlas-rag-search-p95", message)

    def test_local_credentials_do_not_leak_to_output(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OTHER_KEY=ignore\nGRAFANA_ADMIN_USER=operator\n"
                            "GRAFANA_ADMIN_PASSWORD=local-test-only\n")
            self.assertEqual(module.local_grafana_credentials(path),
                             ("operator", "local-test-only"))


if __name__ == "__main__":
    unittest.main()
