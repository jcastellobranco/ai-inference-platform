"""Offline ATLAS CLI contract tests; no Docker, cloud, or external network."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("atlas_cli", ROOT / "scripts/atlas.py")
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)

class CLIContracts(unittest.TestCase):
    def test_fastapi_secure_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            class Args:
                name = "billing-api"
                destination = Path(tmp)
                runtime = "fastapi"
                database = "postgres"
                cache = "redis"
                auth = "jwt"
                observability = "metrics"
            self.assertEqual(atlas.create(Args), 0)
            root = Path(tmp) / Args.name
            self.assertIn("jwt.decode", (root / "app/main.py").read_text())
            self.assertIn("generate_latest", (root / "app/main.py").read_text())
            self.assertIn("JWT_SECRET", (root / "compose.yaml").read_text())
            self.assertIn("DATABASE_URL", (root / "compose.yaml").read_text())
            self.assertIn("REDIS_URL", (root / "compose.yaml").read_text())
            self.assertNotIn("password123", (root / "compose.yaml").read_text())
            self.assertTrue((root / "atlas-service.json").exists())
            with self.assertRaises(FileExistsError):
                atlas.create(Args)

    def test_node_secure_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            class Args:
                name = "events-api"
                destination = Path(tmp)
                runtime = "node"
                database = "none"
                cache = "none"
                auth = "jwt"
                observability = "metrics"
            self.assertEqual(atlas.create(Args), 0)
            root = Path(tmp) / Args.name
            self.assertIn("jwtVerify", (root / "src/server.mjs").read_text())
            self.assertIn("prom-client", (root / "package.json").read_text())
            self.assertIn("USER node", (root / "Dockerfile").read_text())

if __name__ == "__main__":
    unittest.main()
