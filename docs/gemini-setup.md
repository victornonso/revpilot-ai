# Gemini development connection

RevPilot supports Gemini's documented OpenAI-compatible tool-calling endpoint.
The key remains server-side; it is never a NEXT_PUBLIC variable or browser input.

Use the ignored `.env.llm` file:

```dotenv
LLM_PROVIDER=gemini
LLM_TIER=free
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-3.1-flash-lite
LLM_API_KEY=
```

The model name follows the official documentation checked 15 October 2026;
availability and active project quotas must still be checked in AI Studio.
Do not enable billing automatically. A key from an eligible free-tier project
allows local testing, subject to that project's quotas. A multi-tool investigation
can consume multiple provider requests; the orchestration has a four-round limit.

Google's current terms require Paid Services when making API clients available
to users in the UK, EEA or Switzerland. The local free-tier configuration is
therefore blocked for a public app origin. Public deployment must keep AI disabled
or use an explicitly selected, permitted provider/tier. No upgrade is automatic.

The demonstration sends only synthetic Northstar Cloud data. Live company use
requires a review of provider data handling, permissions and applicable terms.

Official references:
- https://ai.google.dev/gemini-api/docs/openai
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/terms

## Investigation lifecycle

Each investigation is saved as running, completed or failed. Tool executions and
evidence remain tenant-scoped in PostgreSQL and can be reopened through the
saved-investigation API and interface, including after a provider failure.

The provider client retries transport errors and transient 5xx responses at most
three times. A 429 stops immediately and records a cooldown using Retry-After
when supplied (60 seconds otherwise). Configuration failures are distinguished
from capacity failures. Cooldowns are persisted per organisation, provider and
model, so a process restart does not reset them. An advisory transaction lock
prevents concurrent requests from starting overlapping provider runs for the
same workspace and model.

Investigations allow at most ten executed tools and four provider rounds. The
last round disables tools and requires an evidence-grounded answer with explicit
limitations. Empty answers fail explicitly. Provider work has an 85-second total
deadline; the browser allows 100 seconds. No automatic paid upgrade or provider
switch is performed. Model configuration is explicit and server-side.

Verification on 15 October 2026: Gemini 3.1 Flash-Lite returned a real
August/September invoiced-revenue comparison using compare_periods; its completed
run and evidence were retrieved from PostgreSQL. Gemini 3.8 Flash returned
high-demand 503 responses during the same check. Free-tier model capacity and
quotas remain external constraints; local recovery tests do not promise provider
availability.
