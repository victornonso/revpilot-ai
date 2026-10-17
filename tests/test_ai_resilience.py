import asyncio
from contextlib import contextmanager
from uuid import uuid4

import httpx
import pytest

from services.ai_analyst import orchestration as ai


@pytest.mark.parametrize(
    "statuses,expected",
    [
        ([503, 200], 200),
        ([503, 503, 503], 503),
        ([429], 429),
        ([401], 401),
        ([400], 400),
        ([402], 402),
    ],
)
def test_provider_retries_only_transient_failures(monkeypatch, statuses, expected):
    calls = []

    async def no_wait(_):
        pass

    monkeypatch.setattr(ai.asyncio, "sleep", no_wait)

    def respond(request):
        status = statuses[len(calls)]
        calls.append(request)
        return httpx.Response(status, json={})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            if expected == 200:
                assert (await ai.request_completion(client, {})).status_code == 200
            else:
                with pytest.raises(ai.ProviderUnavailableError):
                    await ai.request_completion(client, {})

    asyncio.run(run())
    assert len(calls) == len(statuses)


@pytest.mark.parametrize("provider", ["deepseek", "openai"])
@pytest.mark.parametrize("calls_per_round,rounds,executions", [(1, 4, 3), (11, 2, 10)])
def test_final_round_produces_answer_without_more_tools(
    monkeypatch, provider, calls_per_round, rounds, executions
):
    from apps.api import main

    payloads = []
    executed = []

    @contextmanager
    def fake_session():
        yield None

    async def completion(_, payload):
        payloads.append(payload)
        message = (
            {"role": "assistant", "content": "Verified answer with limitations."}
            if payload["tool_choice"] == "none"
            else {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": str(uuid4()),
                        "type": "function",
                        "function": {
                            "name": "list_available_metrics",
                            "arguments": "{}",
                        },
                    }
                    for _ in range(calls_per_round)
                ],
            }
        )
        return httpx.Response(
            200,
            json={"choices": [{"message": message}]},
            request=httpx.Request("POST", "https://provider.example"),
        )

    monkeypatch.setattr(ai.settings, "llm_provider", provider)
    monkeypatch.setattr(ai.settings, "llm_api_key", "test-only")
    monkeypatch.setattr(ai.settings, "llm_model", "fixture")
    monkeypatch.setattr(ai, "session", fake_session)
    monkeypatch.setattr(main, "store", lambda *args: {"id": uuid4()})

    def execute(*args):
        executed.append(args)
        return {"metric": "invoiced"}

    monkeypatch.setattr(ai, "execute", execute)
    monkeypatch.setattr(ai, "request_completion", completion)
    result = asyncio.run(ai._investigate("Explain revenue", {"id": uuid4()}))
    if provider == "deepseek":
        assert all(p["thinking"] == {"type": "disabled"} for p in payloads)
        assert all(
            "max_tokens" in p and "max_completion_tokens" not in p for p in payloads
        )
    assert len(payloads) == rounds
    assert payloads[-1]["tool_choice"] == "none"
    assert len(executed) == executions
    assert result["answer"] == "Verified answer with limitations."


def test_workspace_rejects_concurrent_provider_runs(monkeypatch):
    from sqlalchemy import text

    monkeypatch.setattr(ai.settings, "llm_model", "fixture-" + str(uuid4()))
    model = ai.settings.llm_model

    async def run():
        started = asyncio.Event()
        release = asyncio.Event()

        async def complete(question, conversation):
            started.set()
            await release.wait()
            return {"answer": "Fixture answer", "evidence": []}

        monkeypatch.setattr(ai, "_investigate", complete)
        first = asyncio.create_task(ai.investigate("First fixture"))
        await started.wait()
        try:
            with pytest.raises(ai.ProviderUnavailableError, match="already running"):
                await ai.investigate("Concurrent fixture")
        finally:
            release.set()
            await first

    try:
        asyncio.run(run())
    finally:
        with ai.session() as conn:
            conn.execute(
                text(
                    "DELETE FROM ai.message WHERE payload->>'conversation_id' IN (SELECT id::text FROM ai.conversation WHERE payload->>'model'=:model)"
                ),
                {"model": model},
            )
            conn.execute(
                text("DELETE FROM ai.conversation WHERE payload->>'model'=:model"),
                {"model": model},
            )


def test_failed_run_and_cooldown_survive_new_request(monkeypatch):
    from sqlalchemy import text

    calls = []
    monkeypatch.setattr(ai.settings, "llm_model", "fixture-" + str(uuid4()))
    model = ai.settings.llm_model

    async def fail(*args):
        calls.append(True)
        raise ai.ProviderUnavailableError("Fixture provider busy", "rate_limited", 60)

    monkeypatch.setattr(ai, "_investigate", fail)
    try:
        for _ in range(2):
            with pytest.raises(ai.ProviderUnavailableError):
                asyncio.run(ai.investigate("Fixture resilience check"))
        assert len(calls) == 1
        with ai.session() as conn:
            saved = ai.rows(
                conn,
                "SELECT id,status,payload FROM ai.conversation WHERE payload->>'model'=:model",
                {"model": model},
            )
        assert len(saved) == 1
        assert saved[0]["status"] == "failed"
        assert saved[0]["payload"]["failure_code"] == "rate_limited"
        from fastapi.testclient import TestClient

        from apps.api.main import app

        response = TestClient(app).get("/api/v1/investigations/" + str(saved[0]["id"]))
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["answer"] == "Fixture provider busy"
    finally:
        with ai.session() as conn:
            conn.execute(
                text(
                    "DELETE FROM ai.message WHERE payload->>'conversation_id' IN (SELECT id::text FROM ai.conversation WHERE payload->>'model'=:model)"
                ),
                {"model": model},
            )
            conn.execute(
                text("DELETE FROM ai.conversation WHERE payload->>'model'=:model"),
                {"model": model},
            )
