"""File-backed JWT credentials and safe local bootstrap for generated services."""
from __future__ import annotations
from pathlib import Path

BOOTSTRAP = '''"""Generate an untracked HS256 secret and .env only if absent."""
from pathlib import Path
import os
import secrets

ROOT = Path(__file__).resolve().parent.parent

def main():
    directory = ROOT / ".secrets"
    directory.mkdir(mode=0o700, exist_ok=True)
    secret_file = directory / "atlas_jwt_secret"
    if not secret_file.exists():
        fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(secrets.token_urlsafe(48))
        print("Created untracked JWT secret")
    else:
        print("Preserved JWT secret")
    env_file = ROOT / ".env"
    if not env_file.exists():
        fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write((ROOT / ".env.example").read_text(encoding="utf-8"))
        print("Created .env from example")
    else:
        print("Preserved .env")

if __name__ == "__main__":
    main()
'''

def harden_auth(target: Path, runtime: str) -> None:
    if runtime == "fastapi":
        source = target / "app/main.py"
        text = source.read_text()
        old = '    secret = os.getenv("JWT_SECRET", "")'
        new = (
            '    secret_file = os.getenv("JWT_SECRET_FILE", "/run/secrets/atlas_jwt_secret")\n'
            '    try:\n'
            '        with open(secret_file, encoding="utf-8") as handle:\n'
            '            secret = handle.read().strip()\n'
            '    except OSError:\n'
            '        secret = ""'
        )
        if old not in text:
            raise ValueError("Unexpected FastAPI auth template version")
        source.write_text(text.replace(old, new))
        tests = target / "tests/test_health.py"
        tests.write_text(tests.read_text() +
            '\nimport time\nimport jwt\n\n'
            'def test_jwt_verification(tmp_path, monkeypatch):\n'
            '    secret = "test-secret-strong-enough-for-hs256-jwt-validation"\n'
            '    file = tmp_path / "jwt_secret"\n'
            '    file.write_text(secret)\n'
            '    monkeypatch.setenv("JWT_SECRET_FILE", str(file))\n'
            '    monkeypatch.setenv("JWT_ISSUER", "atlas-local")\n'
            '    monkeypatch.setenv("JWT_AUDIENCE", "atlas-services")\n'
            '    claims = {"sub": "alice", "tenant_id": "tenant-a",\n'
            '              "iss": "atlas-local", "aud": "atlas-services",\n'
            '              "exp": int(time.time()) + 60}\n'
            '    token = jwt.encode(claims, secret, algorithm="HS256")\n'
            '    client = TestClient(app)\n'
            '    response = client.get("/v1/me", headers={"Authorization": "Bearer " + token})\n'
            '    assert response.status_code == 200\n'
            '    assert response.json() == {"subject": "alice", "tenant": "tenant-a"}\n'
            '    claims.pop("tenant_id")\n'
            '    invalid = jwt.encode(claims, secret, algorithm="HS256")\n'
            '    assert client.get("/v1/me", headers={"Authorization": "Bearer " + invalid}).status_code == 401\n'
            '    monkeypatch.setenv("JWT_SECRET_FILE", str(tmp_path / "missing"))\n'
            '    assert client.get("/v1/me", headers={"Authorization": "Bearer " + token}).status_code == 503\n')
    elif runtime == "node":
        source = target / "src/server.mjs"
        text = source.read_text()
        old = "    const secret = process.env.JWT_SECRET || '';"
        new = (
            "    let secret = '';\n"
            "    try { secret = readFileSync(process.env.JWT_SECRET_FILE || "
            "'/run/secrets/atlas_jwt_secret', 'utf8').trim(); } catch {}"
        )
        if old not in text:
            raise ValueError("Unexpected Node auth template version")
        source.write_text("import {readFileSync} from 'node:fs';\n" + text.replace(old, new))
        tests = target / "test/auth.test.mjs"
        tests.write_text(
            "import {test} from 'node:test';\n"
            "import {strict as assert} from 'node:assert';\n"
            "import {mkdtempSync, writeFileSync, rmSync} from 'node:fs';\n"
            "import {tmpdir} from 'node:os';\n"
            "import {join} from 'node:path';\n"
            "import {SignJWT} from 'jose';\n"
            "import {server} from '../src/server.mjs';\n"
            "test('JWT claims and secret file', async () => {\n"
            "  const dir = mkdtempSync(join(tmpdir(), 'atlas-jwt-'));\n"
            "  const file = join(dir, 'secret');\n"
            "  const secret = 'test-secret-strong-enough-for-hs256-jwt-validation';\n"
            "  writeFileSync(file, secret);\n"
            "  process.env.JWT_SECRET_FILE = file;\n"
            "  process.env.JWT_ISSUER = 'atlas-local';\n"
            "  process.env.JWT_AUDIENCE = 'atlas-services';\n"
            "  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));\n"
            "  try {\n"
            "    const url = 'http://127.0.0.1:' + server.address().port + '/v1/me';\n"
            "    const issue = payload => new SignJWT(payload).setProtectedHeader({alg:'HS256'})\n"
            "      .setIssuer('atlas-local').setAudience('atlas-services')\n"
            "      .setSubject('alice').setExpirationTime('5m')\n"
            "      .sign(new TextEncoder().encode(secret));\n"
            "    const good = await issue({tenant_id:'tenant-a'});\n"
            "    const response = await fetch(url, {headers:{authorization:'Bearer ' + good}});\n"
            "    assert.equal(response.status,200);\n"
            "    assert.deepEqual(await response.json(), {subject:'alice',tenant:'tenant-a'});\n"
            "    const bad = await issue({});\n"
            "    assert.equal((await fetch(url,{headers:{authorization:'Bearer ' + bad}})).status,401);\n"
            "    process.env.JWT_SECRET_FILE = join(dir,'missing');\n"
            "    assert.equal((await fetch(url,{headers:{authorization:'Bearer ' + good}})).status,503);\n"
            "  } finally {\n"
            "    await new Promise(resolve => server.close(resolve));\n"
            "    rmSync(dir,{recursive:true,force:true});\n"
            "    delete process.env.JWT_SECRET_FILE;\n"
            "    delete process.env.JWT_ISSUER;\n"
            "    delete process.env.JWT_AUDIENCE;\n"
            "  }\n"
            "});\n"
        )
    else:
        raise ValueError("Unsupported runtime")

    compose = target / "compose.yaml"
    text = compose.read_text()
    old = next((line for line in text.splitlines() if line.strip().startswith("JWT_SECRET:")), None)
    if old is None:
        raise ValueError("Unexpected JWT Compose template")
    text = text.replace(old, "      JWT_SECRET_FILE: /run/secrets/atlas_jwt_secret")
    text = text.replace("    build: .\n", "    build: .\n    secrets:\n      - atlas_jwt_secret\n")
    text += "\nsecrets:\n  atlas_jwt_secret:\n    file: ./.secrets/atlas_jwt_secret\n"
    compose.write_text(text)
    env = target / ".env.example"
    env.write_text(env.read_text().replace("JWT_SECRET=\n", "# Secret mounted from .secrets/atlas_jwt_secret\n"))
    (target / "scripts").mkdir(exist_ok=True)
    (target / "scripts/init_local.py").write_text(BOOTSTRAP)
    (target / "Makefile").write_text(
        ".PHONY: init config up down logs test\n"
        "init:\n\t@python3 scripts/init_local.py\n"
        "config:\n\t@docker compose config --quiet\n"
        "up:\n\t@docker compose up -d --build\n"
        "down:\n\t@docker compose down\n"
        "logs:\n\t@docker compose logs -f --tail=100\n"
        + ("test:\n\t@python3 -m pytest -q\n" if runtime == "fastapi" else
           "test:\n\t@npm test\n")
    )
    doc = target / "README.md"
    doc.write_text(doc.read_text() +
        "\nRun \`make init\` before Compose. The untracked JWT secret is mounted as "
        "a Compose file secret, never embedded in the YAML or environment. "
        "HS256 is a starter contract, not a production identity provider. "
        "Tenant-scoped access control must be implemented separately.\n")
