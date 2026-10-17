"""Provision only the explicitly configured, isolated RevPilot hosted database."""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
connection = (LOCAL / "hosted-database-url").read_text().strip()
if connection.startswith("psql '"):
    connection = connection[6:-1]
parsed = urlsplit(connection)
if (
    parsed.scheme not in ("postgres", "postgresql")
    or not parsed.hostname.endswith(".neon.tech")
    or parsed.path != "/revpilot_db"
):
    raise RuntimeError("Expected an explicitly configured Neon revpilot_db connection.")
config_path = LOCAL / "hosted-demo.json"
if config_path.exists():
    config = json.loads(config_path.read_text())
else:
    password = secrets.token_urlsafe(32)
    app_connection = urlunsplit(
        parsed._replace(netloc=f"revpilot_app:{quote(password)}@{parsed.hostname}")
    )
    config = {
        "DATABASE_URL": app_connection.replace(
            "postgresql://", "postgresql+psycopg://", 1
        ),
        "MIGRATION_DATABASE_URL": connection.replace(
            "postgresql://", "postgresql+psycopg://", 1
        ),
        "APP_DATABASE_PASSWORD": password,
        "SESSION_SECRET": secrets.token_urlsafe(48),
        "PRIVATE_ACCESS_KEY": secrets.token_urlsafe(32),
        "PUBLIC_DEMO_MODE": "true",
        "PRIVATE_ANALYST_ENABLED": "true",
        "DEMO_MODE": "true",
        "APP_ORIGIN": "https://revpilot-ai.vercel.app",
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    (LOCAL / "owner-access.txt").write_text(
        config["PRIVATE_ACCESS_KEY"], encoding="utf-8"
    )
with psycopg.connect(connection) as conn:
    if not conn.execute(
        "SELECT 1 FROM pg_roles WHERE rolname='revpilot_app'"
    ).fetchone():
        conn.execute(
            sql.SQL(
                "CREATE ROLE revpilot_app LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE"
            ).format(sql.Literal(config["APP_DATABASE_PASSWORD"]))
        )
env = {**os.environ, **{k: str(v) for k, v in config.items()}}
for command in (
    ["-m", "alembic", "upgrade", "head"],
    ["-m", "demo.generator.seed"],
    ["-m", "tools.build_marts"],
    ["-m", "services.intelligence.train"],
):
    subprocess.run([sys.executable, *command], cwd=ROOT, env=env, check=True)
print("Hosted RevPilot migrations, demo data, marts and model benchmarks are ready.")
