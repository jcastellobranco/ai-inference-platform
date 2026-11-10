"""Local-first self-service service generator.

Safe defaults: no credentials, no cloud resources, no overwrites.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

def scaffold(name: str, destination: Path, *, runtime: str = "fastapi",
             postgres: bool = False, redis: bool = False) -> Path:
    if not NAME.fullmatch(name) or len(name) > 48:
        raise ValueError("Use lowercase kebab-case service name (max 48 characters)")
    if runtime not in ("fastapi", "node"):
        raise ValueError("Runtime must be fastapi or node")
    target = destination / name
    target.mkdir(parents=True, exist_ok=False)
    def write(path: str, data: str) -> None:
        file = target / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data, encoding="utf-8")
    if runtime == "fastapi":
        write("app/__init__.py", "")
        write("app/main.py", 'from fastapi import FastAPI\n\n'
              f'app = FastAPI(title="{name}")\n\n'
              '@app.get("/health/live")\ndef live():\n    return {"status": "ok"}\n\n'
              '@app.get("/health/ready")\ndef ready():\n    return {"status": "ready"}\n')
        write("requirements.txt", "fastapi>=0.115,<1\nuvicorn>=0.30,<1\n")
        write("Dockerfile", "FROM python:3.12-slim\n"
              "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\nWORKDIR /app\n"
              "COPY requirements.txt .\n"
              "RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app\n"
              "COPY app/ ./app/\nUSER 10001:10001\nEXPOSE 8000\n"
              'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n')
        write("tests/test_health.py", "from fastapi.testclient import TestClient\n"
              "from app.main import app\n\n"
              "def test_health():\n"
              '    assert TestClient(app).get("/health/live").json() == {"status": "ok"}\n')
        write("requirements-dev.txt", "-r requirements.txt\nhttpx>=0.27,<1\npytest>=8,<10\n")
        check = "pip install -r requirements-dev.txt && pytest -q"
    else:
        write("src/server.mjs", "import http from 'node:http';\n"
              "const port = Number(process.env.PORT || 8000);\n"
              "const server = http.createServer((req, res) => {\n"
              "  const path = req.url?.split('?')[0];\n"
              "  if (req.method === 'GET' && (path === '/health/live' || path === '/health/ready')) {\n"
              "    res.writeHead(200, {'content-type': 'application/json'});\n"
              "    res.end(JSON.stringify({status: path.endsWith('ready') ? 'ready' : 'ok'}));\n"
              "    return;\n  }\n"
              "  res.writeHead(404, {'content-type': 'application/json'});\n"
              "  res.end(JSON.stringify({error: 'not_found'}));\n"
              "});\n"
              "if (import.meta.url === new URL('file://' + process.argv[1]).href) server.listen(port, '0.0.0.0');\n"
              "export {server};\n")
        write("test/health.test.mjs", "import {test} from 'node:test';\n"
              "import {strict as assert} from 'node:assert';\n"
              "import {server} from '../src/server.mjs';\n"
              "test('health endpoint', async () => {\n"
              "  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));\n"
              "  try {\n"
              "    const {port} = server.address();\n"
              "    const response = await fetch('http://127.0.0.1:' + port + '/health/live');\n"
              "    assert.equal(response.status, 200);\n"
              "    assert.deepEqual(await response.json(), {status: 'ok'});\n"
              "  } finally { await new Promise(resolve => server.close(resolve)); }\n"
              "});\n")
        write("package.json", '{\n  "name": "' + name + '",\n  "private": true,\n'
              '  "type": "module",\n  "scripts": {"start": "node src/server.mjs", "test": "node --test"}\n}\n')
        write("Dockerfile", "FROM node:22-alpine\nWORKDIR /app\n"
              "COPY --chown=node:node package.json ./\n"
              "COPY --chown=node:node src/ ./src/\n"
              "USER node\nEXPOSE 8000\nCMD [\"node\", \"src/server.mjs\"]\n")
        check = "npm test"
    write(".dockerignore", ".env\n.env.*\n.secrets/\n__pycache__/\n.venv/\nnode_modules/\n.git/\n")
    write(".gitignore", ".env\n.env.*\n!.env.example\n.secrets/\nnode_modules/\n__pycache__/\n.venv/\n")
    write(".github/workflows/ci.yml", "name: CI\non: [push, pull_request]\n"
          "jobs:\n  verify:\n    runs-on: ubuntu-latest\n    permissions:\n      contents: read\n"
          "    steps:\n      - uses: actions/checkout@v4\n"
          + ("      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n"
             if runtime == "fastapi" else
             "      - uses: actions/setup-node@v4\n        with:\n          node-version: '22'\n")
          + f"      - run: {check}\n")
    environment = ["      PORT: '8000'"]
    if postgres:
        environment.append("      DATABASE_URL: ${DATABASE_URL:?Set DATABASE_URL in an untracked .env}")
    if redis:
        environment.append("      REDIS_URL: ${REDIS_URL:?Set REDIS_URL in an untracked .env}")
    write("compose.yaml", "services:\n  app:\n    build: .\n    ports:\n      - '127.0.0.1:8000:8000'\n"
          "    environment:\n" + "\n".join(environment) + "\n"
          "    healthcheck:\n      test: ['CMD', " +
          ("'python', '-c', \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')\""
           if runtime == "fastapi" else
           "'node', '-e', \"fetch('http://127.0.0.1:8000/health/live').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))\"")
          + "]\n      interval: 10s\n      timeout: 3s\n      retries: 5\n")
    write(".env.example", ("DATABASE_URL=\n" if postgres else "") + ("REDIS_URL=\n" if redis else ""))
    write("README.md", f"# {name}\n\nATLAS local service template ({runtime}).\n\n"
          "Run: `docker compose up --build`; health: `/health/live`, `/health/ready`.\n"
          f"Optional external dependencies: postgres={postgres}, redis={redis}. "
          "No database or Redis server is provisioned automatically.\n\n"
          "This template does not implement authentication, authorization, database migrations, "
          "distributed tracing or production-ready readiness checks. Add these before deploying.\n")
    return target

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--destination", type=Path, default=ROOT.parent)
    parser.add_argument("--runtime", choices=("fastapi", "node"), default="fastapi")
    parser.add_argument("--postgres", action="store_true")
    parser.add_argument("--redis", action="store_true")
    args = parser.parse_args()
    try:
        result = scaffold(args.name, args.destination, runtime=args.runtime,
                          postgres=args.postgres, redis=args.redis)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Created {result}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
