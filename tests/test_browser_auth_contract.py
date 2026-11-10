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
        self.assertIn("showPassword ? 'text' : 'password'", dialog)
        self.assertNotIn("Paste a short-lived developer JWT", dialog)
        api = (ROOT / "frontend/src/lib/api.ts").read_text()
        self.assertIn("credentials: 'same-origin'", api)
        self.assertIn("X-CSRF-Token", api)

    def test_unstyled_buttons_have_atlas_theme(self):
        button = (ROOT / "frontend/src/components/ui/Button.tsx").read_text()
        css = (ROOT / "frontend/src/style.css").read_text()
        dialog = (ROOT / "frontend/src/components/AccessDialog.tsx").read_text()
        self.assertIn("`button-${variant}`", button)
        self.assertIn("button.button-unstyled,.button-unstyled", css)
        self.assertIn("appearance:none", css)
        for name in ("auth-reveal", "auth-signout"):
            self.assertIn(f'className="{name}"', dialog)
            self.assertIn(f".auth-dialog .{name}", css)
        self.assertIn("background:#1b2a43", css)

    def test_proxy_preserves_external_port(self):
        nginx = (ROOT / "frontend/nginx.conf").read_text()
        self.assertIn("proxy_set_header Host $http_host;", nginx)
        self.assertIn("proxy_set_header X-Forwarded-Proto $scheme;", nginx)

    def test_migration_and_compose(self):
        migration = (ROOT / "backend/migrations/012_browser_auth.sql").read_text()
        compose = (ROOT / "docker-compose.fullstack.yml").read_text()
        for table in ("app_users", "browser_sessions", "auth_attempts"):
            self.assertIn(table, migration)
        self.assertIn("012_browser_auth.sql", compose)
        self.assertIn("ATLAS_BOOTSTRAP_EMAIL", compose)

if __name__ == "__main__":
    unittest.main()
