"""Generate a minimal FastAPI service skeleton with standard operational endpoints.

Uses stdlib only. Never overwrites existing directories or writes credentials.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

def scaffold(name: str, destination: Path) -> Path:
    if not NAME.fullmatch(name) or len(name) > 48:
        raise ValueError("Use lowercase kebab-case service name (max 48 characters)")
    target = destination / name
    target.mkdir(parents=True, exist_ok=False)
    (target / "app").mkdir()
    (target / "app" / "__init__.py").write_text("")
    (target / "app" / "main.py").write_text(
        'from fastapi import FastAPI\n\n'
        f'app = FastAPI(title="{name}")\n\n'
        '@app.get("/health/live")\n'
        'def live():\n    return {"status": "ok"}\n\n'
        '@app.get("/health/ready")\n'
        'def ready():\n    return {"status": "ready"}\n'
    )
    (target / "requirements.txt").write_text("fastapi>=0.115,<1\nuvicorn>=0.30,<1\n")
    (target / "Dockerfile").write_text(
        "FROM python:3.12-slim\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\n"
        "WORKDIR /app\n"
        "COPY requirements.txt .\n"
        "RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app\n"
        "COPY app/ ./app/\n"
        "USER 10001:10001\n"
        "EXPOSE 8000\n"
        'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
    )
    (target / ".dockerignore").write_text(".env\n.secrets/\n__pycache__/\n.venv/\n")
    (target / "README.md").write_text(
        f"# {name}\n\nATLAS service template.\n\n"
        "Run: `docker build -t local-service .` then `docker run --rm -p 8000:8000 local-service`.\n"
        "Health: `GET /health/live` and `GET /health/ready`.\n\n"
        "Add JWT/tenant authorization, metrics, CI, dependencies and tests before production.\n"
    )
    return target

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--destination", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    try:
        result = scaffold(args.name, args.destination)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Created {result}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
