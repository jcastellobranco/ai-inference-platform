"""ATLAS self-service CLI: create, inspect and validate independent local services.

No cloud calls, secrets, Docker invocation or automatic changes to existing services.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from scaffold_service import ROOT, NAME, scaffold
from atlas_runtime import enhance
from atlas_security import harden_auth
from atlas_registry import catalog, validate_service

def extend_fastapi(target: Path, auth: bool, metrics: bool) -> None:
    requirements = target / "requirements.txt"
    requirements.write_text(requirements.read_text() +
                            ("PyJWT>=2.9,<3\n" if auth else "") +
                            ("prometheus-client>=0.21,<1\n" if metrics else ""))
    source = ["from fastapi import FastAPI, Depends, HTTPException",
              "from fastapi.responses import Response", "import os"]
    if auth:
        source += ["import jwt", "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials"]
    if metrics:
        source += ["from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST",
                   'REQUESTS = Counter("atlas_http_requests_total", "HTTP requests", ["route"])']
    source += ["", 'app = FastAPI(title=' + repr(target.name) + ')', ""]
    if auth:
        source += [
            "bearer = HTTPBearer()",
            "def principal(credentials: HTTPAuthorizationCredentials = Depends(bearer)):",
            '    secret = os.getenv("JWT_SECRET", "")',
            '    issuer = os.getenv("JWT_ISSUER", "")',
            '    audience = os.getenv("JWT_AUDIENCE", "")',
            "    if len(secret) < 32 or not issuer or not audience:",
            '        raise HTTPException(503, "JWT configuration missing")',
            "    try:",
            '        claims = jwt.decode(credentials.credentials, secret, algorithms=["HS256"],',
            '                            issuer=issuer, audience=audience,',
            '                            options={"require": ["sub", "exp", "iss", "aud", "tenant_id"]})',
            '        if not isinstance(claims.get("tenant_id"), str) or not claims["tenant_id"]:',
            '            raise ValueError("tenant missing")',
            "        return claims",
            "    except (jwt.PyJWTError, ValueError):",
            '        raise HTTPException(401, "Invalid token")',
            ""
        ]
    source += ['@app.get("/health/live")', 'def live():', '    return {"status": "ok"}', "",
               '@app.get("/health/ready")', 'def ready():', '    return {"status": "ready"}', ""]
    if auth:
        source += ['@app.get("/v1/me")', 'def me(claims=Depends(principal)):', 
                   '    return {"subject": claims["sub"], "tenant": claims["tenant_id"]}', ""]
    if metrics:
        source += ['@app.get("/metrics", include_in_schema=False)',
                   'def metrics():', '    REQUESTS.labels(route="/metrics").inc()',
                   '    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)', ""]
    (target / "app/main.py").write_text("\n".join(source) + "\n")
    if auth:
        (target / ".env.example").write_text((target / ".env.example").read_text() +
              "JWT_SECRET=\nJWT_ISSUER=atlas-local\nJWT_AUDIENCE=atlas-services\n")
        compose = target / "compose.yaml"
        compose.write_text(compose.read_text().replace("      PORT: '8000'",
              "      PORT: '8000'\n      JWT_SECRET: ${JWT_SECRET:?Set JWT_SECRET in .env}\n"
              "      JWT_ISSUER: ${JWT_ISSUER:-atlas-local}\n"
              "      JWT_AUDIENCE: ${JWT_AUDIENCE:-atlas-services}"))

def extend_node(target: Path, auth: bool, metrics: bool) -> None:
    pkg = target / "package.json"
    data = json.loads(pkg.read_text())
    dependencies = {}
    if auth:
        dependencies["jose"] = "^6.0.0"
    if metrics:
        dependencies["prom-client"] = "^15.1.0"
    if dependencies:
        data["dependencies"] = dependencies
    pkg.write_text(json.dumps(data, indent=2) + "\n")
    if dependencies:
        dockerfile = target / "Dockerfile"
        dockerfile.write_text(dockerfile.read_text().replace(
            "COPY --chown=node:node src/ ./src/",
            "RUN npm install --omit=dev --no-audit --no-fund\nCOPY --chown=node:node src/ ./src/"))

    source = ["import http from 'node:http';"]
    if auth:
        source += ["import {jwtVerify} from 'jose';"]
    if metrics:
        source += ["import client from 'prom-client';",
                   "const requests = new client.Counter({name: 'atlas_http_requests_total', help: 'HTTP requests', labelNames: ['route']});"]
    source += ["const port = Number(process.env.PORT || 8000);",
               "const send = (res, status, body) => {res.writeHead(status, {'content-type':'application/json'}); res.end(JSON.stringify(body));};",
               "const server = http.createServer(async (req, res) => {",
               "  const path = req.url?.split('?')[0];",
               "  if (req.method === 'GET' && (path === '/health/live' || path === '/health/ready')) {",
               "    send(res, 200, {status: path.endsWith('ready') ? 'ready' : 'ok'}); return;",
               "  }"]
    if metrics:
        source += ["  if (req.method === 'GET' && path === '/metrics') {",
                   "    requests.inc({route:'/metrics'});",
                   "    res.writeHead(200, {'content-type':client.register.contentType});",
                   "    res.end(await client.register.metrics()); return;",
                   "  }"]
    if auth:
        source += ["  if (req.method === 'GET' && path === '/v1/me') {",
                   "    const secret = process.env.JWT_SECRET || '';",
                   "    const issuer = process.env.JWT_ISSUER || '';",
                   "    const audience = process.env.JWT_AUDIENCE || '';",
                   "    if (secret.length < 32 || !issuer || !audience) {send(res,503,{error:'auth_not_configured'});return;}",
                   "    const header = req.headers.authorization || '';",
                   "    if (!header.startsWith('Bearer ')) {send(res,401,{error:'unauthorized'});return;}",
                   "    try {",
                   "      const {payload} = await jwtVerify(header.slice(7), new TextEncoder().encode(secret),",
                   "        {issuer, audience, algorithms:['HS256']});",
                   "      if (!payload.sub || !payload.tenant_id || typeof payload.tenant_id !== 'string') throw Error('missing claims');",
                   "      send(res,200,{subject:payload.sub,tenant:payload.tenant_id});",
                   "    } catch {send(res,401,{error:'unauthorized'});}",
                   "    return;",
                   "  }"]
    source += ["  send(res,404,{error:'not_found'});",
               "});",
               "if (import.meta.url === new URL('file://' + process.argv[1]).href) server.listen(port, '0.0.0.0');",
               "export {server};"]
    (target / "src/server.mjs").write_text("\n".join(source) + "\n")
    if auth:
        (target / ".env.example").write_text((target / ".env.example").read_text() +
              "JWT_SECRET=\nJWT_ISSUER=atlas-local\nJWT_AUDIENCE=atlas-services\n")
        compose = target / "compose.yaml"
        compose.write_text(compose.read_text().replace("      PORT: '8000'",
              "      PORT: '8000'\n      JWT_SECRET: ${JWT_SECRET:?Set JWT_SECRET in .env}\n"
              "      JWT_ISSUER: ${JWT_ISSUER:-atlas-local}\n"
              "      JWT_AUDIENCE: ${JWT_AUDIENCE:-atlas-services}"))

def create(args) -> int:
    if not NAME.fullmatch(args.name) or len(args.name) > 48:
        raise ValueError("Use lowercase kebab-case service name (max 48 chars)")
    destination = Path(args.destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / args.name
    lock = destination / (".atlas-create-" + args.name + ".lock")
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Service exists: {target}")
        with tempfile.TemporaryDirectory(dir=destination, prefix=".atlas-stage-") as temporary:
            staged = scaffold(args.name, Path(temporary), runtime=args.runtime,
                              postgres=args.database == "postgres",
                              redis=args.cache == "redis")
            if args.runtime == "fastapi":
                extend_fastapi(staged, args.auth == "jwt",
                               args.observability == "metrics")
            else:
                extend_node(staged, args.auth == "jwt",
                            args.observability == "metrics")
            enhance(staged, args.runtime, postgres=args.database == "postgres",
                    redis=args.cache == "redis", metrics=args.observability == "metrics")
            if args.auth == "jwt":
                harden_auth(staged, args.runtime)
            else:
                scripts = staged / "scripts"
                scripts.mkdir(exist_ok=True)
                (scripts / "init_local.py").write_text(
                    '"""Initialize local configuration once."""\n'
                    'from pathlib import Path\nimport os\n'
                    'root = Path(__file__).resolve().parent.parent\n'
                    'source = root / ".env.example"\n'
                    'target = root / ".env"\n'
                    'if not target.exists():\n'
                    '    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)\n'
                    '    with os.fdopen(fd, "w") as output:\n'
                    '        output.write(source.read_text())\n'
                )
                (staged / "Makefile").write_text(
                    ".PHONY: init config up down logs test\n"
                    "init:\n\t@python3 scripts/init_local.py\n"
                    "config:\n\t@docker compose config --quiet\n"
                    "up:\n\t@docker compose up -d --build\n"
                    "down:\n\t@docker compose down\n"
                    "logs:\n\t@docker compose logs -f --tail=100\n"
                    + ("test:\n\t@python3 -m pytest -q\n"
                       if args.runtime == "fastapi" else "test:\n\t@npm test\n")
                )
            compose = staged / "compose.yaml"
            compose.write_text(compose.read_text().replace(
                "'127.0.0.1:8000:8000'",
                "'127.0.0.1:$"+"{ATLAS_HOST_PORT:-8000}:8000'"))
            manifest = {"schema_version": 1, "name": args.name, "runtime": args.runtime,
                        "database": args.database, "cache": args.cache,
                        "auth": args.auth, "observability": args.observability}
            (staged / "atlas-service.json").write_text(
                json.dumps(manifest, indent=2) + "\n")
            (staged / "README.md").write_text(
                (staged / "README.md").read_text() +
                "\nRun `make init` then `make up`. "
                "Use ATLAS_HOST_PORT for multiple local services. "
                "Dependencies have real readiness probes, but no migrations "
                "or tenant authorization policies are created.\n")
            errors = validate_service(staged)
            if errors:
                raise ValueError("Generated service contract failed: " + "; ".join(errors))
            if target.exists() or target.is_symlink():
                raise FileExistsError(f"Service exists: {target}")
            staged.rename(target)
    finally:
        lock.unlink(missing_ok=True)
    print(f"Created {target}")
    return 0

def inspect(path: Path) -> int:
    manifest = json.loads((path / "atlas-service.json").read_text())
    print(json.dumps(manifest, indent=2))
    return 0

def validate(path: Path) -> int:
    errors = validate_service(path.resolve())
    if errors:
        for issue in errors:
            print(f"FAIL: {issue}", file=sys.stderr)
        return 1
    print(f"PASS: {path} satisfies static ATLAS contracts")
    return 0


def list_catalog(root: Path) -> int:
    records = catalog(root.resolve())
    print(json.dumps(records, indent=2))
    return 1 if any(not item["valid"] for item in records) else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="atlas", description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    create_cmd = subs.add_parser("create-service")
    create_cmd.add_argument("name")
    create_cmd.add_argument("--destination", type=Path, default=ROOT.parent)
    create_cmd.add_argument("--runtime", choices=("fastapi", "node"), default="fastapi")
    create_cmd.add_argument("--database", choices=("none", "postgres"), default="none")
    create_cmd.add_argument("--cache", choices=("none", "redis"), default="none")
    create_cmd.add_argument("--auth", choices=("none", "jwt"), default="none")
    create_cmd.add_argument("--observability", choices=("none", "metrics"), default="none")
    validate_cmd = subs.add_parser("validate")
    validate_cmd.add_argument("path", type=Path)
    catalog_cmd = subs.add_parser("catalog")
    catalog_cmd.add_argument("--root", type=Path, default=ROOT.parent)
    inspect_cmd = subs.add_parser("inspect")
    inspect_cmd.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "create-service":
            return create(args)
        if args.command == "inspect":
            return inspect(args.path)
        if args.command == "validate":
            return validate(args.path)
        return list_catalog(args.root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"atlas: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
