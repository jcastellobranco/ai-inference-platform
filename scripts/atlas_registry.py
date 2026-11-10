"""Offline registry and contract checks for generated ATLAS services.

The local catalog is derived from manifests on disk, not a central server.
This module does not read .env contents, contact remote APIs or start containers.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

CHOICES = {
    "runtime": {"fastapi", "node"},
    "database": {"none", "postgres"},
    "cache": {"none", "redis"},
    "auth": {"none", "jwt"},
    "observability": {"none", "metrics"},
}


def load_manifest(directory: Path) -> dict:
    manifest = json.loads((directory / "atlas-service.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    return manifest


def validate_service(directory: Path) -> list[str]:
    """Static contract validation only; does not certify runtime or security."""
    errors: list[str] = []
    if not directory.is_dir() or directory.is_symlink():
        return ["Service directory missing or is a symbolic link"]
    try:
        manifest = load_manifest(directory)
    except (OSError, ValueError) as exc:
        return [f"Invalid manifest: {exc}"]
    if manifest.get("schema_version") != 1:
        errors.append("Unsupported schema_version (expected 1)")
    if manifest.get("name") != directory.name:
        errors.append("Manifest name does not match service directory")
    for key, choices in CHOICES.items():
        if manifest.get(key) not in choices:
            errors.append(f"Invalid {key} value")
    runtime = manifest.get("runtime")
    essential = ["Dockerfile", "compose.yaml", ".dockerignore", ".gitignore",
                 ".env.example", "README.md", ".github/workflows/ci.yml"]
    if runtime == "fastapi":
        essential += ["app/main.py", "requirements.txt",
                      "requirements-dev.txt", "tests/test_health.py"]
    elif runtime == "node":
        essential += ["src/server.mjs", "package.json", "test/health.test.mjs"]
    for filename in essential:
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            errors.append(f"Missing or invalid file: {filename}")
    if errors:
        return errors
    compose = (directory / "compose.yaml").read_text(encoding="utf-8")
    source = ((directory / "app/main.py") if runtime == "fastapi" else
              (directory / "src/server.mjs")).read_text(encoding="utf-8")
    if runtime == "fastapi":
        try:
            ast.parse(source, filename="app/main.py")
        except SyntaxError as exc:
            errors.append(f"Python source syntax: {exc.msg}")
    else:
        try:
            pkg = json.loads((directory / "package.json").read_text())
            if pkg.get("type") != "module":
                errors.append("Node package must declare ESM module type")
        except (OSError, ValueError):
            errors.append("Invalid package.json")
    for endpoint in ("/health/live", "/health/ready"):
        if endpoint not in source:
            errors.append(f"Missing {endpoint} endpoint")
    if "'127.0.0.1:8000:8000'" not in compose:
        errors.append("Local Compose port should bind loopback")
    for option, marker in (("database", "DATABASE_URL"), ("cache", "REDIS_URL")):
        if manifest.get(option) != "none" and marker not in compose:
            errors.append(f"{option} enabled but {marker} missing from Compose")
    if manifest.get("auth") == "jwt":
        if "/v1/me" not in source or "JWT_SECRET" not in compose:
            errors.append("JWT protection contract missing")
        if "JWT_SECRET=" not in (directory / ".env.example").read_text():
            errors.append("JWT configuration template missing")
    if manifest.get("observability") == "metrics" and "/metrics" not in source:
        errors.append("Prometheus endpoint missing")
    return errors


def catalog(root: Path) -> list[dict]:
    if not root.is_dir():
        raise FileNotFoundError(f"No catalog root: {root}")
    services = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and not path.is_symlink() and (path / "atlas-service.json").is_file():
            try:
                manifest = load_manifest(path)
                problems = validate_service(path)
                services.append({"directory": str(path), "service": manifest,
                                 "valid": not problems, "issues": problems})
            except (OSError, ValueError) as exc:
                services.append({"directory": str(path), "valid": False,
                                 "issues": [f"Invalid manifest: {exc}"]})
    return services
