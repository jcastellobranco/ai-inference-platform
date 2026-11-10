"""Golden path release checks; offline and unprivileged by design."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import atlas
from atlas_registry import catalog, validate_service


def args(root, name, *, runtime="fastapi", database="none", cache="none",
         auth="none", observability="none"):
    return SimpleNamespace(destination=Path(root), name=name, runtime=runtime,
                           database=database, cache=cache, auth=auth,
                           observability=observability)


class GoldenPathRelease(unittest.TestCase):
    def test_full_python_generated_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            configuration = args(tmp, "secured-python", database="postgres",
                                 cache="redis", auth="jwt", observability="metrics")
            self.assertEqual(atlas.create(configuration), 0)
            service = Path(tmp) / "secured-python"
            self.assertEqual(validate_service(service), [])
            source = (service / "app/main.py").read_text()
            self.assertIn("psycopg.connect", source)
            self.assertIn("redis_client.Redis.from_url", source)
            self.assertIn("check_dependencies", source)
            self.assertIn('atlas_http_request_duration_seconds', source)
            self.assertIn('JWT_SECRET_FILE', source)
            compose = (service / "compose.yaml").read_text()
            self.assertIn('secrets:', compose)
            self.assertNotIn('JWT_SECRET: ', compose)
            self.assertIn("ATLAS_HOST_PORT", compose)
            self.assertTrue((service / "Makefile").is_file())
            self.assertFalse((service / ".secrets").exists())
            self.assertEqual(len(catalog(Path(tmp))), 1)
            self.assertTrue(catalog(Path(tmp))[0]["valid"])

    def test_full_node_generated_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(atlas.create(args(tmp, "secured-node", runtime="node",
                                              database="postgres", cache="redis",
                                              auth="jwt", observability="metrics")), 0)
            service = Path(tmp) / "secured-node"
            self.assertEqual(validate_service(service), [])
            source = (service / "src/server.mjs").read_text()
            package = (service / "package.json").read_text()
            for expected in ("jwtVerify", "readFileSync", "checkDependencies",
                             "atlas_http_request_duration_seconds"):
                self.assertIn(expected, source)
            for expected in ('"pg"', '"redis"', '"prom-client"', '"jose"'):
                self.assertIn(expected, package)
            self.assertIn("npm install", (service / "Dockerfile").read_text())
            self.assertNotIn("JWT_SECRET: ", (service / "compose.yaml").read_text())

    def test_local_service_init_preserves_existing_secret(self):
        import runpy
        with tempfile.TemporaryDirectory() as tmp:
            atlas.create(args(tmp, "local-secure", auth="jwt"))
            root = Path(tmp) / "local-secure"
            runpy.run_path(str(root / "scripts/init_local.py"), run_name="__main__")
            secret = root / ".secrets/atlas_jwt_secret"
            value = secret.read_text()
            self.assertGreaterEqual(len(value), 40)
            self.assertTrue((root / ".env").exists())
            runpy.run_path(str(root / "scripts/init_local.py"), run_name="__main__")
            self.assertEqual(secret.read_text(), value)

    def test_generation_is_safe_on_collision_or_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "taken").mkdir()
            (path / "taken" / "user.txt").write_text("do not overwrite")
            with self.assertRaises(FileExistsError):
                atlas.create(args(tmp, "taken"))
            self.assertEqual((path / "taken/user.txt").read_text(), "do not overwrite")
            with self.assertRaises(ValueError):
                atlas.create(args(tmp, "partial", runtime="invalid"))
            self.assertFalse((path / "partial").exists())
            self.assertEqual(list(path.glob(".atlas-stage-*")), [])
            self.assertEqual(list(path.glob(".atlas-create-*.lock")), [])

    def test_catalog_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            atlas.create(args(tmp, "service-a"))
            service = Path(tmp) / "service-a"
            self.assertEqual(validate_service(service), [])
            (service / "Dockerfile").unlink()
            self.assertNotEqual(validate_service(service), [])
            listing = catalog(Path(tmp))
            self.assertFalse(listing[0]["valid"])


if __name__ == "__main__":
    unittest.main()
