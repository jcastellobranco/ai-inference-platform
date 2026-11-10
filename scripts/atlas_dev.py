"""ATLAS local-first bootstrap and environment diagnostics.

Only creates local untracked files. Never contacts cloud services or starts containers.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = ("rag-document-intelligence", "llm-evaluation-observability",
            "multi-agent-orchestration", "mcp-tool-platform")

def doctor() -> int:
    problems = []
    if not shutil.which("docker"):
        problems.append("Docker CLI not found")
    else:
        try:
            subprocess.run(["docker", "compose", "version"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except (subprocess.SubprocessError, OSError):
            problems.append("Docker Compose plugin unavailable")
    for name in SIBLINGS:
        location = ROOT.parent / name
        print(f"{'OK' if location.is_dir() else 'OPTIONAL' } sibling: {name}")
    if not (ROOT / ".env").exists():
        problems.append(".env not found; run make init, then configure local secrets")
    if not (ROOT / ".secrets" / "redis_password").exists():
        print("OPTIONAL Redis secret not found; run make init before up-redis")
    for problem in problems:
        print(f"ACTION: {problem}")
    return 1 if problems else 0

def init() -> int:
    env = ROOT / ".env"
    if not env.exists():
        template = ROOT / ".env.example"
        if not template.exists():
            print("Missing .env.example", file=sys.stderr)
            return 1
        env.write_bytes(template.read_bytes())
        try:
            env.chmod(0o600)
        except OSError:
            pass
        print("Created .env from template; replace placeholders before starting services")
    else:
        print("Preserving existing .env")
    directory = ROOT / ".secrets"
    directory.mkdir(mode=0o700, exist_ok=True)
    secret = directory / "redis_password"
    if not secret.exists():
        # Exclusive create: never overwrite a user-provided secret.
        fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(secrets.token_urlsafe(48))
        print("Created local Redis secret; never commit .secrets/")
    else:
        print("Preserving existing Redis secret")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "init"))
    args = parser.parse_args()
    return doctor() if args.action == "doctor" else init()

if __name__ == "__main__":
    raise SystemExit(main())
