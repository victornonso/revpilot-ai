# Deployment and startup

Verified local environment: Windows, Python 3.12.15, Node 24, PostgreSQL 18.6,
Next.js 16.4.1 and official Temporal CLI 1.9.1 development server. Application
port 3010, API 8010, isolated database 5544, Temporal gRPC 7233. The portfolio
and GridSignal use separate directories, databases and web ports.

The native bootstrap locates PostgreSQL through POSTGRES_BIN or the existing
local PostgreSQL 18 distribution. It creates an isolated cluster/database and
distinct administrator/application credentials in ignored .env. Existing demo
records are preserved on repeated generation. .env.llm separately holds optional
provider configuration. Both files remain excluded from Git and container contexts.

Docker Compose defines PostgreSQL, migration/seed/model bootstrap, API, Temporal,
worker and web services. `docker compose config --quiet` passes. Docker execution
is unverified because the local Docker engine is unavailable. Container runtime
compatibility and the complete startup health sequence remain a required check.

## Native Temporal

Use the official CLI development server with a persistent filename:

```powershell
temporal server start-dev --ip 127.0.0.1 --headless --db-filename .local/temporal-state.db
uv run python -m apps.worker.main
```

The development server must not be deployed as a public production service.

## Hosting

No hosted RevPilot URL is claimed. GitHub source is private. Public deployment
needs suitable persistent database, API/worker and Temporal hosting, an OIDC
browser session, secrets configuration, backups, operational monitoring and
completion of the acceptance gaps. No paid services have been purchased or enabled.

Frontend rewrites use API_INTERNAL_URL at build time. Set it to the backend host
before building the container or Vercel application. Keep provider secrets on
the API only. Authenticated API requests use verified OIDC bearer tokens and
database-authoritative organisation membership; the browser login flow is not
yet wired. Production live mode must not be exposed before that work is verified.
