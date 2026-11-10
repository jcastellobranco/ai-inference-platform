"""Offline contract checks for read-only observability smoke script."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("atlas_observability_smoke",
                                              ROOT / "scripts/atlas_observability_smoke.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SmokeTests(unittest.TestCase):
    def test_all_four_targets_up(self):
        targets = {"data": {"activeTargets": [
            {"labels": {"job": name}, "health": "up"} for name in sorted(mod.EXPECTED)
        ]}}
        with patch.object(mod, "get_json", side_effect=[{"database": "ok"}, targets]):
            ok, message = mod.check()
        self.assertTrue(ok, message)

    def test_missing_rag_target_fails(self):
        targets = {"data": {"activeTargets": [
            {"labels": {"job": "atlas-api"}, "health": "up"}
        ]}}
        with patch.object(mod, "get_json", side_effect=[{"database": "ok"}, targets]):
            ok, message = mod.check()
        self.assertFalse(ok)
        self.assertIn("atlas-rag", message)


if __name__ == "__main__":
    unittest.main()
