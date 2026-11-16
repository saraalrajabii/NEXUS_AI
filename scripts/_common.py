"""Shared helpers for the lesson scripts. Standard library only (works with any Python 3.9+)."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def read_env() -> dict:
    if not ENV_FILE.exists():
        sys.exit("No .env file found. Run:  cp .env.example .env")
    values = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def write_env(key: str, value: str) -> None:
    """Set KEY=value in .env (replacing an existing line, or appending)."""
    text = ENV_FILE.read_text()
    line = f"{key}={value}"
    if re.search(rf"^{re.escape(key)}=.*$", text, flags=re.M):
        text = re.sub(rf"^{re.escape(key)}=.*$", lambda _: line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n{line}\n"
    ENV_FILE.write_text(text)


def http(method: str, url: str, body: dict | None = None, headers: dict | None = None, raw: bytes | None = None):
    """Small JSON HTTP helper. Returns (status, parsed JSON or text)."""
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status, payload = resp.status, resp.read()
    except urllib.error.HTTPError as err:
        status, payload = err.code, err.read()
    except urllib.error.URLError as err:
        sys.exit(f"Could not reach {url}: {err.reason}. Is the service running? (docker compose ps)")
    try:
        return status, json.loads(payload or b"null")
    except ValueError:
        return status, payload.decode(errors="replace")


def chatwoot_url(env: dict) -> str:
    """Scripts run on your computer, so they use localhost — not the Docker name chatwoot-rails."""
    return f"http://localhost:{env.get('CHATWOOT_HOST_PORT') or '3000'}"
