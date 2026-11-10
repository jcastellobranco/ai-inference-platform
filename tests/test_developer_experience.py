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
            self.assertTrue((path / "compose.yaml").exists())
            self.assertTrue((path / ".github/workflows/ci.yml").exists())
            with self.assertRaises(FileExistsError):
                mod.scaffold("example-service", Path(tmp))

    def test_node_scaffold_and_optional_dependencies(self):
        mod = load("scripts/scaffold_service.py", "atlas_scaffold_node")
        with tempfile.TemporaryDirectory() as tmp:
            path = mod.scaffold("events-api", Path(tmp), runtime="node",
                                postgres=True, redis=True)
            self.assertTrue((path / "src/server.mjs").exists())
            self.assertIn("USER node", (path / "Dockerfile").read_text())
            self.assertIn("DATABASE_URL", (path / "compose.yaml").read_text())
            self.assertIn("REDIS_URL", (path / "compose.yaml").read_text())
            self.assertNotIn("password123", (path / "compose.yaml").read_text())

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
                env_text = (Path(tmp) / ".env").read_text()
                password_line = next(line for line in env_text.splitlines()
                                     if line.startswith("GRAFANA_ADMIN_PASSWORD="))
                self.assertGreaterEqual(len(password_line.split("=", 1)[1]), 32)
                self.assertEqual(mod.init(), 0)
                self.assertEqual(secret.read_text(), value)
                self.assertEqual((Path(tmp) / ".env").read_text(), env_text)
            finally:
                mod.ROOT = original

class ObservabilityContracts(unittest.TestCase):
    def test_local_observability_overlay(self):
        overlay = (ROOT / "docker-compose.observability.yml").read_text()
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("llm-evaluation-observability/observability/prometheus.yml", overlay)
        self.assertIn("llm-evaluation-observability/observability/grafana", overlay)
        self.assertIn("127.0.0.1:3000:3000", overlay)
        self.assertIn("127.0.0.1:9090:9090", overlay)
        self.assertIn("GRAFANA_ADMIN_PASSWORD:?", overlay)
        self.assertIn("up-observability:", makefile)
        self.assertIn("config-observability:", makefile)


if __name__ == "__main__":
    unittest.main()
