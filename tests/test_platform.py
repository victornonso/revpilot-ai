import hashlib
import hmac
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from apps.api.db import DEMO_ORG, session, settings
from apps.api.main import app
from services.ai_analyst.orchestration import execute
from services.ingestion.connectors import (
    HubSpot,
    ProviderError,
    Stripe,
    verify_stripe_webhook,
)

client = TestClient(app)


@pytest.mark.parametrize(
    "screen",
    [
        "overview",
        "pipeline",
        "forecasting",
        "customers",
        "analyst",
        "automations",
        "recovery",
        "reports",
        "operations",
    ],
)
def test_workspaces_are_database_backed(screen):
    response = client.get("/api/v1/dashboard/" + screen)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["demo"] is True
    assert body["meta"]["source"] == "PostgreSQL analytical views"
    assert body["meta"]["stale"] is False


def test_tenant_boundary_denies_foreign_reads_and_writes():
    other = uuid4()
    with session(other) as conn:
        assert conn.execute(text("SELECT count(*) FROM core.account")).scalar() == 0
        assert (
            conn.execute(text("SELECT count(*) FROM mart.monthly_revenue")).scalar()
            == 0
        )
        with pytest.raises(DBAPIError):
            conn.execute(
                text(
                    "INSERT INTO automation.action(org_id,status) VALUES(:org,'pending')"
                ),
                {"org": DEMO_ORG},
            )


def test_read_connection_is_not_superuser():
    with session() as conn:
        assert (
            conn.execute(
                text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
            ).scalar()
            is False
        )


def test_dates_and_segment_validation():
    assert (
        client.get(
            "/api/v1/dashboard/overview?start=2026-10-14&end=2026-01-01"
        ).status_code
        == 422
    )
    assert client.get("/api/v1/dashboard/overview?segment=Injected").status_code == 422
    assert (
        client.get(
            "/api/v1/dashboard/pipeline?sort=amount;DROP TABLE core.account"
        ).status_code
        == 200
    )


def test_revenue_reconciles_and_segment_cash_is_filtered():
    all = client.get("/api/v1/dashboard/overview").json()
    enterprise = client.get("/api/v1/dashboard/overview?segment=Enterprise").json()
    metrics = lambda d: {
        m["id"]: float(m["value"]) for m in d["metrics"] if m["value"] is not None
    }
    assert 0 < metrics(enterprise)["cash"] < metrics(all)["cash"]
    with session() as conn:
        difference = conn.execute(
            text(
                "SELECT (SELECT sum(amount) FROM finance.invoice)-(SELECT sum(amount) FROM finance.invoice_line)"
            )
        ).scalar()
        assert difference == 0


def test_exact_payload_approval_and_replay_protection():
    opportunity = client.get("/api/v1/dashboard/pipeline").json()["table"][0]
    response = client.post(
        "/api/v1/proposals",
        json={
            "opportunity_id": opportunity["id"],
            "title": "Test approval / exact payload",
        },
    )
    assert response.status_code == 201
    approval = response.json()
    request = {"decision": "reject", "version": approval["version"]}
    assert (
        client.post(
            f"/api/v1/approvals/{approval['id']}/decision", json=request
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/approvals/{approval['id']}/decision", json=request
        ).status_code
        == 409
    )


def test_changed_action_invalidates_approval():
    opportunity = client.get("/api/v1/dashboard/pipeline").json()["table"][0]
    approval = client.post(
        "/api/v1/proposals",
        json={
            "opportunity_id": opportunity["id"],
            "title": "Test mutation / approval protection",
        },
    ).json()
    with session() as conn:
        conn.execute(
            text(
                'UPDATE automation.action SET payload=payload || \'{"title":"Changed"}\'::jsonb WHERE id=:id'
            ),
            {"id": approval["payload"]["action_id"]},
        )
    assert (
        client.post(
            f"/api/v1/approvals/{approval['id']}/decision",
            json={"decision": "approve", "version": 1},
        ).status_code
        == 409
    )


def test_rule_simulation_does_not_create_actions():
    with session() as conn:
        before = conn.execute(text("SELECT count(*) FROM automation.action")).scalar()
    response = client.post(
        "/api/v1/rules/simulate",
        json={"title": "Test dry run", "threshold": 30, "minimum_amount": 10000},
    )
    assert response.status_code == 200 and response.json()
    with session() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM automation.action")).scalar()
            == before
        )


def test_report_formats_are_actual_exports():
    report = client.post(
        "/api/v1/reports",
        json={
            "title": "Verification briefing",
            "start": "2025-11-01",
            "end": "2026-10-14",
            "metrics": ["invoiced", "mrr"],
        },
    ).json()
    csv = client.get(f"/api/v1/reports/{report['id']}/download?format=csv")
    pdf = client.get(f"/api/v1/reports/{report['id']}/download?format=pdf")
    assert csv.status_code == 200 and "Synthetic demonstration" in csv.text
    assert pdf.content.startswith(b"%PDF-")


def test_import_validation_is_transactional():
    preview = client.post(
        "/api/v1/imports/preview",
        files={
            "file": (
                "test.csv",
                b"name,segment,region\nValid,SMB,UK\nInvalid,Unknown,UK\n",
                "text/csv",
            )
        },
    ).json()
    with session() as conn:
        before = conn.execute(text("SELECT count(*) FROM core.account")).scalar()
    response = client.post(
        f"/api/v1/imports/{preview['id']}/confirm",
        json={
            "name_column": "name",
            "segment_column": "segment",
            "region_column": "region",
        },
    )
    assert response.status_code == 422
    with session() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM core.account")).scalar() == before
        )


def test_tools_cannot_run_arbitrary_sql():
    with pytest.raises(ValueError):
        execute("execute_sql", {"sql": "SELECT * FROM identity.user"})


def test_unconfigured_ai_does_not_fake_an_answer(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    assert (
        client.post(
            "/api/v1/investigations", json={"question": "Why did revenue change?"}
        ).status_code
        == 503
    )


def test_cross_origin_mutation_is_denied():
    assert (
        client.post(
            "/api/v1/rules",
            json={"title": "Evil rule"},
            headers={"Origin": "https://untrusted.invalid"},
        ).status_code
        == 403
    )


def test_stripe_signature_checks_raw_body_and_time():
    body = b'{"id":"evt_test"}'
    now = 1800000000
    secret = "fixture-secret"
    signature = hmac.new(
        secret.encode(), str(now).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    assert (
        verify_stripe_webhook(body, f"t={now},v1={signature}", secret, now=now)["id"]
        == "evt_test"
    )
    with pytest.raises(ProviderError):
        verify_stripe_webhook(body + b" ", f"t={now},v1={signature}", secret, now=now)
    with pytest.raises(ProviderError):
        verify_stripe_webhook(body, f"t={now},v1={signature}", secret, now=now + 1000)


def test_connectors_paginate_with_mock_http_contracts():
    import asyncio

    async def run():
        seen = []

        def hubspot(request):
            seen.append(str(request.url))
            return httpx.Response(
                200,
                json={
                    "results": [{"id": "1"}],
                    **(
                        {"paging": {"next": {"after": "2"}}}
                        if "after" not in request.url.params
                        else {}
                    ),
                },
            )

        connector = HubSpot("fixture", transport=httpx.MockTransport(hubspot))
        pages = [page async for page in connector.records("deals")]
        await connector.close()
        assert len(pages) == 2 and "after=2" in seen[-1]

        def stripe(request):
            return httpx.Response(
                200, json={"data": [{"id": "cus_1"}], "has_more": False}
            )

        connector = Stripe("fixture", transport=httpx.MockTransport(stripe))
        pages = [page async for page in connector.records("customers")]
        await connector.close()
        assert pages[0][0][0]["id"] == "cus_1"

    asyncio.run(run())
