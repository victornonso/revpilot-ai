# DeepSeek analyst connection

RevPilot uses DeepSeek Flash through the OpenAI-format chat completion API.
The API key stays in ignored `.env.llm` locally and Render's server environment
when hosted. No provider credential is sent to the frontend.

```dotenv
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_TIER=paid
LLM_API_KEY=<dedicated-server-key>
```

Installations must have a funded DeepSeek API account. Hosting remains on free
plans; model usage is billed separately. Thinking is explicitly disabled for
bounded response times. Investigations allow four provider rounds and ten
validated analytical tool executions, with evidence IDs persisted in PostgreSQL.
The final round cannot request more tools. Private hosted access requires a
signed owner session. Quota, credit and configuration failures are reported
explicitly without a silent provider fallback. These per-run bounds are not a
monthly spending limit.

Restart the API after changing local variables. For hosted configuration, use
`uv run python tools/prepare_hosted_environment.py`, transfer the provider
variables into Render's server environment and deploy the selected source commit.
Never commit `.env.llm` or `.local/render.env`.

- [DeepSeek API format](https://api-docs.deepseek.com/)
- [Thinking and tool calling](https://api-docs.deepseek.com/guides/thinking_mode/)
- [Pricing](https://api-docs.deepseek.com/quick_start/pricing/)
