"""Richer local golden-path wiring for generated ATLAS services.

Keeps optional connections explicit; never provisions external infrastructure or
embeds credentials. All health probes avoid returning underlying connection errors.
"""
from __future__ import annotations

import json
from pathlib import Path


def enhance(target: Path, runtime: str, *, postgres: bool, redis: bool,
            metrics: bool) -> None:
    if runtime == "fastapi":
        _python(target, postgres=postgres, redis=redis, metrics=metrics)
    elif runtime == "node":
        _node(target, postgres=postgres, redis=redis, metrics=metrics)
    else:
        raise ValueError("Unsupported runtime")


def _python(target: Path, *, postgres: bool, redis: bool, metrics: bool) -> None:
    requirements = target / "requirements.txt"
    requirements.write_text(requirements.read_text() +
        ("psycopg[binary]>=3.2,<4\n" if postgres else "") +
        ("redis>=5,<7\n" if redis else ""), encoding="utf-8")
    src = target / "app/main.py"
    body = src.read_text(encoding="utf-8")
    if postgres or redis:
        imports = ["import os"]
        if postgres:
            imports.append("import psycopg")
        if redis:
            imports.append("import redis as redis_client")
        lines = ["", "def check_dependencies():",
                 "    try:"]
        if postgres:
            lines += [
                '        url = os.environ["DATABASE_URL"]',
                "        with psycopg.connect(url, connect_timeout=2) as connection:",
                '            connection.execute("SELECT 1")',
            ]
        if redis:
            lines += [
                '        url = os.environ["REDIS_URL"]',
                "        client = redis_client.Redis.from_url(",
                "            url, socket_connect_timeout=2, socket_timeout=2)",
                "        try:",
                "            client.ping()",
                "        finally:",
                "            client.close()",
            ]
        lines += ["        return True",
                  "    except (Exception,):",
                  "        return False", ""]
        body = "\n".join(imports + [""] + lines) + body
        body = body.replace(
            'def ready():\n    return {"status": "ready"}',
            'def ready():\n'
            '    if not check_dependencies():\n'
            '        raise HTTPException(status_code=503, detail="Dependency unavailable")\n'
            '    return {"status": "ready"}')
        test_path = target / "tests/test_health.py"
        tests = test_path.read_text()
        tests += ("\ndef test_readiness_fails_closed_without_dependencies(monkeypatch):\n"
                  "    monkeypatch.delenv('DATABASE_URL', raising=False)\n"
                  "    monkeypatch.delenv('REDIS_URL', raising=False)\n"
                  '    assert TestClient(app).get("/health/ready").status_code == 503\n')
        test_path.write_text(tests, encoding="utf-8")
    if metrics:
        body = body.replace(
            'REQUESTS = Counter("atlas_http_requests_total", "HTTP requests", ["route"])',
            'REQUESTS = Counter("atlas_http_requests_total", "HTTP requests", '
            '["method", "route", "status"])\n'
            'LATENCY = Histogram("atlas_http_request_duration_seconds", '
            '"HTTP request duration", ["method", "route"])'
        )
        body = body.replace(
            'from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST',
            'from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST'
        )
        middleware = (
            "\nimport time\nfrom fastapi import Request\n\n"
            "@app.middleware('http')\n"
            "async def collect_metrics(request: Request, call_next):\n"
            "    started = time.perf_counter()\n"
            "    status = 500\n"
            "    try:\n"
            "        response = await call_next(request)\n"
            "        status = response.status_code\n"
            "        return response\n"
            "    finally:\n"
            "        route = request.scope.get('route')\n"
            "        path = getattr(route, 'path', '/unmatched')\n"
            "        REQUESTS.labels(method=request.method, route=path,\n"
            "                        status=str(status)).inc()\n"
            "        LATENCY.labels(method=request.method, route=path).observe(\n"
            "            time.perf_counter() - started)\n\n"
        )
        body = body.replace('@app.get("/health/live")', middleware + '@app.get("/health/live")')
        body = body.replace('    REQUESTS.labels(route="/metrics").inc()\n', "")
        (target / "README.md").write_text(
            (target / "README.md").read_text() +
            "\nMetrics: /metrics includes request counts and latency with low-cardinality route templates.\n"
        )
    src.write_text(body, encoding="utf-8")


def _node(target: Path, *, postgres: bool, redis: bool, metrics: bool) -> None:
    pkg_path = target / "package.json"
    package = json.loads(pkg_path.read_text())
    dependencies = package.setdefault("dependencies", {})
    if postgres:
        dependencies["pg"] = "^8.13.0"
    if redis:
        dependencies["redis"] = "^5.0.0"
    if not dependencies:
        package.pop("dependencies", None)
    pkg_path.write_text(json.dumps(package, indent=2) + "\n")
    if postgres or redis:
        docker = target / "Dockerfile"
        text = docker.read_text()
        if "RUN npm install" not in text:
            text = text.replace("COPY --chown=node:node src/ ./src/",
                "RUN npm install --omit=dev --no-audit --no-fund\n"
                "COPY --chown=node:node src/ ./src/")
            docker.write_text(text)
    src = target / "src/server.mjs"
    body = src.read_text()
    if postgres or redis:
        imports = []
        lines = ["async function checkDependencies() {"]
        if postgres:
            imports.extend(["import pg from 'pg';", "const {Client} = pg;"])
            lines.extend([
                "  if (!process.env.DATABASE_URL) throw Error('dependency unavailable');",
                "  const db = new Client({connectionString: process.env.DATABASE_URL,",
                "    connectionTimeoutMillis: 2000});",
                "  let dbConnected = false;",
                "  try {",
                "    await db.connect(); dbConnected = true;",
                "    await db.query('SELECT 1');",
                "  } finally { if (dbConnected) await db.end(); }",
            ])
        if redis:
            imports.append("import {createClient} from 'redis';")
            lines.extend([
                "  if (!process.env.REDIS_URL) throw Error('dependency unavailable');",
                "  const cache = createClient({url: process.env.REDIS_URL,",
                "    socket: {connectTimeout: 2000, reconnectStrategy: false}});",
                "  try {",
                "    await cache.connect();",
                "    await cache.ping();",
                "  } finally {",
                "    if (cache.isOpen) await cache.quit();",
                "    else cache.destroy();",
                "  }",
            ])
        lines.append("}")
        body = "\n".join(imports + lines) + "\n" + body
        body = body.replace(
            "    send(res, 200, {status: path.endsWith('ready') ? 'ready' : 'ok'}); return;",
            "    if (path === '/health/ready') {\n"
            "      try { await checkDependencies(); }\n"
            "      catch { send(res, 503, {status: 'not_ready'}); return; }\n"
            "    }\n"
            "    send(res, 200, {status: path.endsWith('ready') ? 'ready' : 'ok'}); return;"
        )
        test = target / "test/health.test.mjs"
        tests = test.read_text()
        # Standalone check: the test runner starts its own HTTP server and
        # does not require a running Postgres/Redis instance.
        tests += ("\ntest('unconfigured dependencies are not ready', async () => {\n"
                  "  const oldDb = process.env.DATABASE_URL;\n"
                  "  const oldRedis = process.env.REDIS_URL;\n"
                  "  delete process.env.DATABASE_URL;\n"
                  "  delete process.env.REDIS_URL;\n"
                  "  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));\n"
                  "  try {\n"
                  "    const {port} = server.address();\n"
                  "    const response = await fetch('http://127.0.0.1:' + port + '/health/ready');\n"
                  "    assert.equal(response.status, 503);\n"
                  "  } finally {\n"
                  "    await new Promise(resolve => server.close(resolve));\n"
                  "    if (oldDb !== undefined) process.env.DATABASE_URL = oldDb;\n"
                  "    if (oldRedis !== undefined) process.env.REDIS_URL = oldRedis;\n"
                  "  }\n"
                  "});\n")
        test.write_text(tests)
    if metrics:
        body = body.replace(
            "const requests = new client.Counter({name: 'atlas_http_requests_total', help: 'HTTP requests', labelNames: ['route']});",
            "const requests = new client.Counter({name: 'atlas_http_requests_total', help: 'HTTP requests', "
            "labelNames: ['method', 'route', 'status']});\n"
            "const latency = new client.Histogram({name: 'atlas_http_request_duration_seconds', "
            "help: 'HTTP request duration', labelNames: ['method', 'route']});"
        )
        hook = (
            "  const started = process.hrtime.bigint();\n"
            "  res.once('finish', () => {\n"
            "    const route = ['/health/live', '/health/ready', '/v1/me', '/metrics'].includes(path)\n"
            "      ? path : '/unmatched';\n"
            "    requests.inc({method: req.method, route, status: String(res.statusCode)});\n"
            "    latency.observe({method: req.method, route},\n"
            "      Number(process.hrtime.bigint() - started) / 1e9);\n"
            "  });\n"
        )
        body = body.replace("  const path = req.url?.split('?')[0];\n",
                            "  const path = req.url?.split('?')[0];\n" + hook)
        body = body.replace("    requests.inc({route:'/metrics'});\n", "")
        (target / "README.md").write_text(
            (target / "README.md").read_text() +
            "\nMetrics: /metrics includes request counts and latency with bounded route labels.\n"
        )
    spec = {
        "openapi": "3.1.0",
        "info": {"title": target.name, "version": "0.1.0"},
        "paths": {
            "/health/live": {"get": {"responses": {"200": {"description": "Alive"}}}},
            "/health/ready": {"get": {"responses": {"200": {"description": "Ready"},
                                                       "503": {"description": "Not ready"}}}},
        },
    }
    if "/v1/me" in body:
        spec["paths"]["/v1/me"] = {
            "get": {"security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Authenticated principal"},
                                  "401": {"description": "Invalid token"}}}}
        spec["components"] = {"securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}}
    if metrics:
        spec["paths"]["/metrics"] = {"get": {
            "responses": {"200": {"description": "Prometheus text metrics"}}}}
    body = body.replace(
        "const server = http.createServer",
        "const OPENAPI = " + json.dumps(spec, separators=(",", ":")) + ";\n"
        "const server = http.createServer"
    )
    body = body.replace(
        "  send(res,404,{error:'not_found'});",
        "  if (req.method === 'GET' && path === '/openapi.json') "
        "{ send(res,200,OPENAPI); return; }\n"
        "  send(res,404,{error:'not_found'});"
    )
    src.write_text(body)
