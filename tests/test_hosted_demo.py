"""Public browsing must never grant access to the private analyst or shared writes."""

import jwt
import pytest
from fastapi.testclient import TestClient

from apps.api.db import settings
from apps.api.main import app, limits


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setattr(settings, "public_demo_mode", True)
    monkeypatch.setattr(settings, "public_analyst_enabled", False)
    monkeypatch.setattr(settings, "private_access_key", "test-owner-access-fixture")
    monkeypatch.setattr(settings, "session_secret", "test-signing-fixture-" * 4)
    limits.clear()
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    limits.clear()


def test_public_demo_is_read_only_and_hides_private_investigations(hosted):
    response = hosted.get("/api/v1/dashboard/analyst")
    assert response.status_code == 200
    assert response.json()["meta"]["stale"] is False
    assert response.json()["private_access_required"] is True
    assert response.json()["conversations"] == []
    assert (
        hosted.post("/api/v1/investigations", json={"question": "Revenue?"}).status_code
        == 403
    )
    assert hosted.post("/api/v1/rules", json={}).status_code == 403
    assert hosted.post("/api/v1/imports/preview", json={}).status_code == 403


def test_owner_session_is_signed_secure_and_can_be_revoked(hosted):
    assert (
        hosted.post("/api/v1/access/unlock", json={"key": "wrong"}).status_code == 401
    )
    response = hosted.post(
        "/api/v1/access/unlock", json={"key": "test-owner-access-fixture"}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    assert hosted.get("/api/v1/session").json()["role"] == "demo_owner"
    assert (
        hosted.get("/api/v1/dashboard/analyst").json()["private_access_required"]
        is False
    )
    # The owner analyst session does not turn the shared demo into a mutable tenant.
    assert hosted.post("/api/v1/rules", json={}).status_code == 403
    hosted.post("/api/v1/access/lock")
    assert hosted.get("/api/v1/session").json()["role"] == "demo_viewer"


def test_forged_owner_cookie_and_repeated_access_attempts_are_rejected(hosted):
    token = jwt.encode(
        {"sub": "owner", "aud": "revpilot-owner", "exp": 9999999999},
        "different-signing-key" * 4,
        algorithm="HS256",
    )
    hosted.cookies.set("revpilot_access", token)
    assert hosted.get("/api/v1/session").json()["role"] == "demo_viewer"
    for _ in range(5):
        assert (
            hosted.post("/api/v1/access/unlock", json={"key": "wrong"}).status_code
            == 401
        )
    assert (
        hosted.post("/api/v1/access/unlock", json={"key": "wrong"}).status_code == 429
    )


def test_public_analyst_sessions_are_isolated_and_usage_is_bounded(hosted, monkeypatch):
    from uuid import uuid4

    from sqlalchemy import text

    from apps.api.db import session
    from services.ai_analyst import orchestration as ai

    model = "public-fixture-" + str(uuid4())
    monkeypatch.setattr(settings, "public_analyst_enabled", True)
    monkeypatch.setattr(settings, "llm_api_key", "test-only")
    monkeypatch.setattr(settings, "llm_model", model)
    calls = []

    async def complete(question, conversation):
        calls.append(question)
        return {
            "conversation_id": str(conversation["id"]),
            "answer": "Verified fixture",
            "evidence": [],
        }

    monkeypatch.setattr(ai, "_investigate", complete)
    try:
        response = hosted.get("/api/v1/dashboard/analyst")
        assert response.json()["configured"] is True
        assert response.json()["private_access_required"] is False
        assert response.json()["conversations"] == []
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie
        for index in range(3):
            result = hosted.post(
                "/api/v1/investigations",
                json={"question": f"Public fixture question {index}"},
            )
            assert result.status_code == 200
        conversation_id = result.json()["conversation_id"]
        assert (
            hosted.get(f"/api/v1/investigations/{conversation_id}").status_code == 200
        )
        assert len(hosted.get("/api/v1/dashboard/analyst").json()["conversations"]) == 3
        assert (
            hosted.post(
                "/api/v1/investigations", json={"question": "Over quota fixture"}
            ).status_code
            == 429
        )
        assert len(calls) == 3
        with TestClient(app, base_url="https://testserver") as other:
            assert other.get("/api/v1/dashboard/analyst").json()["conversations"] == []
            assert (
                other.get(f"/api/v1/investigations/{conversation_id}").status_code
                == 404
            )
        hosted.cookies.set("revpilot_visitor", "forged-cookie")
        assert hosted.get("/api/v1/dashboard/analyst").json()["conversations"] == []
    finally:
        with session() as conn:
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
