"""Provider-specific wire formats for bounded analytical tool calls."""


def completion_payload(provider, model, messages, tools, final_round):
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "none" if final_round else "auto",
    }
    token_parameter = (
        "max_tokens" if provider == "deepseek" else "max_completion_tokens"
    )
    payload[token_parameter] = 3000 if final_round else 1800
    if provider == "deepseek":
        # Bounded tool retrieval supplies the evidence; avoid unbounded reasoning
        # latency and reasoning-token charges for the interactive demo.
        payload["thinking"] = {"type": "disabled"}
    return payload
