"""Offline tests for the developer golden path helpers."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class GoldenPathTests(unittest.TestCase):
    def test_scaffold_creates_minimal_service(self):
        mod = load("scripts/scaffold_service.py", "atlas_scaffold")
        with tempfile.TemporaryDirectory() as tmp:
            path = mod.scaffold("example-service", Path(tmp))
            self.assertTrue((path / "Dockerfile").exists())
            self.assertIn("/health/live", (path / "app/main.py").read_text())
            self.assertIn("USER 10001", (path / "Dockerfile").read_text())
            with self.assertRaises(FileExistsError):
                mod.scaffold("example-service", Path(tmp))

    def test_scaffold_rejects_invalid_name(self):
        mod = load("scripts/scaffold_service.py", "atlas_scaffold_invalid")
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("../../escape", "UPPER", "with space", "bad_name"):
                with self.assertRaises(ValueError):
                    mod.scaffold(name, Path(tmp))

    def test_bootstrap_does_not_overwrite_existing_secrets(self):
        mod = load("scripts/atlas_dev.py", "atlas_dev")
        with tempfile.TemporaryDirectory() as tmp:
            original = mod.ROOT
            try:
                mod.ROOT = Path(tmp)
                (Path(tmp) / ".env.example").write_text("PLACEHOLDER=1\n")
                self.assertEqual(mod.init(), 0)
                secret = Path(tmp) / ".secrets/redis_password"
                value = secret.read_text()
                self.assertGreaterEqual(len(value), 32)
                self.assertEqual(mod.init(), 0)
                self.assertEqual(secret.read_text(), value)
            finally:
                mod.ROOT = original

if __name__ == "__main__":
    unittest.main()
