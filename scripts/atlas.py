"""ATLAS self-service CLI: create, inspect and validate independent local services.

No cloud calls, secrets, Docker invocation or automatic changes to existing services.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from scaffold_service import ROOT, scaffold

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
    if args.auth != "none" and args.auth != "jwt":
        raise ValueError("Unsupported authentication mode")
    if args.observability not in ("none", "metrics"):
        raise ValueError("Unsupported observability mode")
    target = scaffold(args.name, args.destination, runtime=args.runtime,
                      postgres=args.database == "postgres", redis=args.cache == "redis")
    if args.runtime == "fastapi":
        extend_fastapi(target, args.auth == "jwt", args.observability == "metrics")
    else:
        extend_node(target, args.auth == "jwt", args.observability == "metrics")
    manifest = {"schema_version": 1, "name": args.name, "runtime": args.runtime,
                "database": args.database, "cache": args.cache, "auth": args.auth,
                "observability": args.observability}
    (target / "atlas-service.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (target / "README.md").write_text((target / "README.md").read_text() +
          "\nGenerated optional capabilities are starter integrations, not production security certification.\n"
          "JWT mode validates HS256 signature, issuer, audience, expiry, subject and tenant.\n"
          "Metrics mode exposes /metrics; it does not yet provide distributed tracing.\n"
          "Database/cache flags create configuration placeholders, not database migrations or connection pools.\n")
    print(f"Created {target}")
    return 0

def inspect(path: Path) -> int:
    manifest = json.loads((path / "atlas-service.json").read_text())
    print(json.dumps(manifest, indent=2))
    return 0

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
    inspect_cmd = subs.add_parser("inspect")
    inspect_cmd.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        return create(args) if args.command == "create-service" else inspect(args.path)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"atlas: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
