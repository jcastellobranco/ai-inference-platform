"""Offline security contract tests for local browser sessions."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class BrowserAuthContract(unittest.TestCase):
    def test_backend_python_parses(self):
        for name in ("main.py", "browser_auth.py"):
            source = (ROOT / "backend/app" / name).read_text()
            ast.parse(source, filename=name)

    def test_auth_contract(self):
        source = (ROOT / "backend/app/browser_auth.py").read_text()
        for expected in ("httponly=True", '"lax"', "csrf_hash", "compare_digest",
                         "PasswordHash.recommended()", "ATLAS_BOOTSTRAP_EMAIL",
                         "browser_sessions", "auth_attempts", "DELETE FROM browser_sessions"):
            self.assertIn(expected, source)
        self.assertNotIn("password123", source)

    def test_frontend_uses_session(self):
        dialog = (ROOT / "frontend/src/components/AccessDialog.tsx").read_text()
        self.assertIn("/api/auth/", dialog)
        self.assertIn("type=\"password\"", dialog)
        self.assertNotIn("Paste a short-lived developer JWT", dialog)
        api = (ROOT / "frontend/src/lib/api.ts").read_text()
        self.assertIn("credentials: 'same-origin'", api)
        self.assertIn("X-CSRF-Token", api)

    def test_migration_and_compose(self):
        migration = (ROOT / "backend/migrations/012_browser_auth.sql").read_text()
        compose = (ROOT / "docker-compose.fullstack.yml").read_text()
        for table in ("app_users", "browser_sessions", "auth_attempts"):
            self.assertIn(table, migration)
        self.assertIn("012_browser_auth.sql", compose)
        self.assertIn("ATLAS_BOOTSTRAP_EMAIL", compose)

if __name__ == "__main__":
    unittest.main()
