# AI governance

The provider loop exposes ten allowlisted analytical/action tools. It accepts no
arbitrary SQL, applies typed filters and UUID parsing, and uses tenant-scoped
database transactions. Action proposals also check the caller's role. The loop
has a maximum of ten tools and four provider rounds, bounded output tokens and
HTTP timeouts. Tool results, messages and evidence references are persisted.

The system instruction distinguishes evidence, interpretation, uncertainty and
recommendations; user text and source records are untrusted evidence. No provider
key means an explicit unavailable state, not a fabricated assistant response.
Provider responses are rendered as escaped text. Contact PII is not an analytical
tool input or output. Exact-payload approval is required before any action executes.

DeepSeek uses a funded, server-only API key and bounded analytical tool calls;
see [provider configuration](deepseek-setup.md). Credentials are excluded from
Git and client bundles. Recruiters receive signed HTTP-only visitor sessions.
Saved investigations are scoped to that session, and PostgreSQL enforces
per-visitor, per-network and global rolling usage limits before provider calls.

Live grounding is verified locally and on the hosted recruiter experience.
Broader adversarial evaluations remain necessary: prompt instructions alone
are not a complete prompt-injection defence. Role checks, typed parameters and
allowlisted operations provide the execution boundary. Production governance
also needs retention controls, token accounting and structured response validation.
