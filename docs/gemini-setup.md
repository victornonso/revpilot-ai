# Gemini development connection

RevPilot supports Gemini's documented OpenAI-compatible tool-calling endpoint.
The key remains server-side; it is never a NEXT_PUBLIC variable or browser input.

Use the ignored `.env.llm` file:

```dotenv
LLM_PROVIDER=gemini
LLM_TIER=free
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-3.8-flash
LLM_API_KEY=
```

The model name follows the official documentation checked 14 October 2026;
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
