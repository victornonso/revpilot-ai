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

## Hosted portfolio edition

The portfolio edition runs on Vercel Hobby, Render Free and a separate Neon Free
PostgreSQL 18 project. The GitHub repository is public. The database is provisioned
with separate owner/migration and non-superuser application roles. API runtime
configuration receives only application-role database access; schema migration
credentials remain outside the hosted API.

`PUBLIC_DEMO_MODE=true` grants anonymous read access to analytical views and
exports. It does not grant shared-record writes or access to private
owner investigations. `PUBLIC_ANALYST_ENABLED=true` enables recruiter investigations
with separate signed visitor sessions and persisted usage limits. `PRIVATE_ACCESS_KEY` unlocks an eight-hour owner session, signed
with `SESSION_SECRET` and stored in a secure HTTP-only, same-site cookie. Failed
unlock attempts are rate-limited. Private access can be explicitly locked again.

`PRIVATE_ANALYST_ENABLED=true` permits the owner's configured model provider
behind that session. With public analyst access enabled, recruiters can also run bounded investigations.
Provider credentials are kept in Render's server-side environment. The access
key is generated in ignored `.local/owner-access.txt`; do not commit it or place
it in a client environment variable.

The public edition does not run a Temporal development server or imply that
external automations execute. Approval execution and shared commercial writes
remain available in the local workspace, separate from the public demo.

The dataset is generated once and preserved. `meta.stale` is false for demo
organisations, and the interface displays a quiet demo label. A dashboard query
refresh does not acquire new business records. Failed API requests continue to
surface as errors.

Render may sleep when idle, and Neon scales its compute to zero. Cold requests
can take longer; no paid instance or artificial keep-alive is required.

Frontend rewrites use API_INTERNAL_URL at build time. Set it to the backend host
before building the container or Vercel application. Keep provider secrets on
the API only. Commercial connected-organisation mode uses verified OIDC bearer
tokens and database-authoritative membership. Its browser login flow remains
separate acceptance work; the portfolio demo is not that production mode.

To prepare an isolated hosted demonstration, save its Neon connection in ignored
`.local/hosted-database-url` and run `uv run python tools/provision_hosted_demo.py`.
The utility validates the target database, creates the application role, applies
migrations, seeds the demo, builds SQL marts and records model benchmarks.

## DeepSeek analyst configuration

Set these variables on the API service only, or in ignored `.env.llm` for the
local workspace:

```dotenv
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_TIER=paid
LLM_API_KEY=<dedicated-server-key>
```

The adapter uses DeepSeek's OpenAI-format chat completion endpoint, explicitly
disables thinking, and limits output to 1,800 tokens per retrieval round and
3,000 in the final round. Investigations retain four provider rounds, ten
authorised tool executions, an 85-second deadline and one concurrent run per
workspace. Tool results remain tenant-scoped and persisted with evidence IDs.
These execution limits bound individual runs; they are not a monthly spend cap.
Paid API credits are required, independently of the free hosting services.
Insufficient-credit responses stop immediately and persist a retry window.
There is no silent fallback to another paid provider.

Hosted recruiter access is enabled with `PUBLIC_ANALYST_ENABLED=true`. Signed
HTTP-only visitor cookies isolate investigation histories and saved results.
PostgreSQL enforces three runs per visitor per hour, ten per HMAC-hashed network
identifier per rolling day and fifty visitor runs per rolling day across the
demo, under the same transaction lock as concurrent-run admission. Clearing
cookies does not reset the network or global quotas. No raw IP is stored in
investigation records. Owner investigations remain outside visitor histories.
Switching providers does not expose keys or owner investigations to visitors. The generated commercial dataset contains demonstration records.

Use `uv run python tools/prepare_hosted_environment.py` to prepare ignored
`.local/render.env` with standard dotenv parsing, application-role database
credentials and the selected provider tier. Never commit that file. Restart
the API or redeploy after changing provider variables.

Provider protocol: [DeepSeek thinking and tool calls](https://api-docs.deepseek.com/guides/thinking_mode/).
