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

Gemini free quota is prepared for local development; see gemini-setup.md. No key
is configured or committed. Public UK deployment requires a permitted provider
tier under Google's current terms. Billing is not enabled automatically.

Live provider grounding and adversarial provider tests remain unverified until
an authorised key is connected. Prompt instructions alone are not a complete
prompt-injection defence; permissions and allowlisted operations are the hard
boundary. Production governance still needs retention controls, token accounting,
structured response validation and broader adversarial evaluations.
