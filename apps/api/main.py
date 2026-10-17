import csv
import hashlib
import hmac
import io
import json
import logging
import time
from collections import defaultdict, deque
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from .analytics import CATALOGUE, dashboard
from .auth import authenticate, permitted, role, tenant
from .db import rows, session, settings

app = FastAPI(title="RevPilot API", version="0.1.0")
log = logging.getLogger("revpilot")
limits = defaultdict(deque)
SCREENS = {
    "overview",
    "pipeline",
    "forecasting",
    "customers",
    "analyst",
    "automations",
    "recovery",
    "reports",
    "operations",
}


@app.middleware("http")
async def boundary(request: Request, call_next):
    request_id = str(uuid4())
    begin = time.monotonic()
    ip = request.client.host if request.client else "unknown"
    window = limits[ip]
    now = time.monotonic()
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) > 240:
        return JSONResponse({"detail": "Too many requests. Retry shortly."}, 429)
    window.append(now)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != settings.app_origin:
            return JSONResponse({"detail": "Origin is not authorised."}, 403)
    if request.url.path.startswith("/api/"):
        try:
            organisation, member_role = authenticate(request)
            tenant.set(organisation)
            role.set(member_role)
            if not permitted(request.url.path, request.method):
                return JSONResponse(
                    {"detail": "Your role cannot perform this action."}, 403
                )
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, exc.status_code)
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_failed", extra={"request_id": request_id})
        response = JSONResponse(
            {"detail": "The request could not be completed.", "request_id": request_id},
            500,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    log.info(
        "%s %s %s %.3f",
        request_id,
        request.method,
        request.url.path,
        time.monotonic() - begin,
    )
    return response


class Meta(BaseModel):
    model_config = ConfigDict(extra="allow")
    demo: bool
    organisation: str
    period: dict
    source: str


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    metrics: list[dict]
    charts: list[dict]
    table: list[dict]
    total: int
    page: int
    meta: Meta


def dates(start: date | None, end: date | None):
    start = start or date(2025, 11, 1)
    end = end or date(2026, 10, 14)
    if start > end or (end - start).days > 1100:
        raise HTTPException(
            422, "Choose an ordered reporting period of at most 1,100 days."
        )
    return datetime.combine(start, datetime.min.time(), UTC), datetime.combine(
        end + timedelta(days=1), datetime.min.time(), UTC
    )


def store(conn, table, payload, status="saved", key=None):
    return rows(
        conn,
        f"INSERT INTO {table}(org_id,status,payload,idempotency_key) VALUES(:org,:status,cast(:payload as jsonb),:key) ON CONFLICT(org_id,idempotency_key) DO UPDATE SET idempotency_key=excluded.idempotency_key RETURNING id,status,payload,version,created_at",
        {
            "org": str(tenant.get()),
            "status": status,
            "payload": json.dumps(payload, default=str),
            "key": key,
        },
    )[0]


@app.get("/health")
def health():
    with session() as c:
        c.execute(text("SELECT 1"))
    return {"status": "ok", "database": "PostgreSQL", "demo": settings.demo_mode}


class PrivateAccess(BaseModel):
    key: str = Field(min_length=1, max_length=256)


@app.post("/api/v1/access/unlock")
def unlock_private_analyst(body: PrivateAccess, request: Request):
    ip = request.client.host if request.client else "unknown"
    attempts = limits["unlock:" + ip]
    now = time.monotonic()
    while attempts and attempts[0] < now - 600:
        attempts.popleft()
    if len(attempts) >= 5:
        raise HTTPException(429, "Too many access attempts. Try again in ten minutes.")
    attempts.append(now)
    if (
        not settings.public_demo_mode
        or not settings.private_access_key
        or not hmac.compare_digest(
            body.key.encode(), settings.private_access_key.encode()
        )
    ):
        raise HTTPException(401, "Access key is not valid.")
    token = jwt.encode(
        {
            "sub": "owner",
            "aud": "revpilot-owner",
            "exp": datetime.now(UTC) + timedelta(hours=8),
        },
        settings.session_secret,
        algorithm="HS256",
    )
    response = JSONResponse({"unlocked": True})
    response.set_cookie(
        "revpilot_access",
        token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=28800,
    )
    return response


@app.post("/api/v1/access/lock")
def lock_private_analyst():
    response = JSONResponse({"unlocked": False})
    response.delete_cookie(
        "revpilot_access", secure=True, httponly=True, samesite="strict"
    )
    return response


@app.get("/api/v1/session")
def identity():
    with session() as conn:
        organisation = rows(conn, "SELECT id,name,demo FROM identity.organisation")[0]
    return {
        "organisation": str(organisation["id"]),
        "name": organisation["name"],
        "mode": "Synthetic demonstration"
        if organisation["demo"]
        else "Connected organisation",
        "role": role.get(),
        "external_execution": False,
    }


@app.get("/api/v1/dashboard/{screen}", response_model=DashboardResponse)
def get_screen(
    screen: str,
    start: date | None = None,
    end: date | None = None,
    segment: str = "All",
    search: str = Query(default="", max_length=100),
    sort: str = "amount",
    direction: str = "desc",
    page: int = 1,
    stage: str = "All",
    owner: str = "All",
):
    if screen not in SCREENS:
        raise HTTPException(404, "Unknown workspace.")
    if segment not in ("All", "SMB", "Mid-market", "Enterprise"):
        raise HTTPException(422, "Unknown segment.")
    if page < 1 or page > 10000:
        raise HTTPException(422, "Invalid page.")
    if stage not in (
        "All",
        "Discovery",
        "Qualified",
        "Proposal",
        "Negotiation",
        "Won",
        "Lost",
    ):
        raise HTTPException(422, "Unknown opportunity stage.")
    if owner != "All":
        try:
            UUID(owner)
        except ValueError as exc:
            raise HTTPException(422, "Invalid owner.") from exc
    begin, finish = dates(start, end)
    with session() as c:
        return dashboard(
            c,
            screen,
            begin,
            finish,
            segment,
            search,
            sort,
            direction,
            page,
            stage,
            owner,
        )


@app.get("/api/v1/metrics")
def catalogue():
    return [
        {"id": k, "label": v[0], "unit": v[1], "definition": v[2]}
        for k, v in CATALOGUE.items()
    ]


@app.get("/api/v1/search")
def search(q: str = ""):
    if len(q) < 2:
        return []
    with session() as c:
        return rows(
            c,
            "SELECT id,name,'customers' route FROM core.account WHERE name ILIKE :q UNION ALL SELECT id,name,'pipeline' route FROM core.opportunity WHERE name ILIKE :q LIMIT 20",
            {"q": f"%{q[:100]}%"},
        )


@app.get("/api/v1/details/{kind}/{record_id}")
def details(kind: str, record_id: UUID):
    with session() as c:
        if kind in ("pipeline", "recovery"):
            record = rows(
                c, "SELECT * FROM mart.pipeline WHERE id=:id", {"id": record_id}
            )
            if not record:
                raise HTTPException(404, "Opportunity not found.")
            return {
                "record": record[0],
                "history": rows(
                    c,
                    "SELECT from_stage,to_stage,occurred_at FROM core.opportunity_stage_history WHERE opportunity_id=:id ORDER BY occurred_at",
                    {"id": record_id},
                ),
                "activities": rows(
                    c,
                    "SELECT kind,occurred_at FROM core.activity WHERE opportunity_id=:id ORDER BY occurred_at DESC LIMIT 30",
                    {"id": record_id},
                ),
                "prediction": rows(
                    c,
                    "SELECT payload,created_at FROM ml.prediction WHERE payload->>'entity_id'=:id ORDER BY created_at DESC LIMIT 1",
                    {"id": str(record_id)},
                ),
            }
        if kind == "customers":
            record = rows(
                c, "SELECT * FROM core.account WHERE id=:id", {"id": record_id}
            )
            if not record:
                raise HTTPException(404, "Account not found.")
            return {
                "record": record[0],
                "subscriptions": rows(
                    c,
                    "SELECT monthly_amount,started_at,ended_at FROM finance.subscription WHERE account_id=:id",
                    {"id": record_id},
                ),
                "invoices": rows(
                    c,
                    "SELECT issued_at,amount,outstanding FROM mart.invoice_balance WHERE account_id=:id ORDER BY issued_at DESC LIMIT 20",
                    {"id": record_id},
                ),
                "opportunities": rows(
                    c,
                    "SELECT name,stage,amount,expected_close FROM core.opportunity WHERE account_id=:id ORDER BY created_at DESC LIMIT 20",
                    {"id": record_id},
                ),
            }
        raise HTTPException(404, "Unknown detail type.")


class Proposal(BaseModel):
    opportunity_id: UUID
    title: str = Field(min_length=3, max_length=150)
    note: str = Field(default="", max_length=2000)


@app.post("/api/v1/proposals", status_code=201)
def propose(body: Proposal):
    with session() as c:
        opportunity = rows(
            c,
            "SELECT id,name,owner_id,amount,days_in_stage FROM mart.pipeline WHERE id=:id",
            {"id": body.opportunity_id},
        )
        if not opportunity:
            raise HTTPException(404, "Opportunity not found.")
        payload = {
            "title": body.title,
            "note": body.note,
            "opportunity": opportunity[0],
            "adapter": "isolated-demo",
            "action_type": "internal_follow_up",
            "version": 1,
        }
        action = store(c, "automation.action", payload, "pending")
        digest = hashlib.sha256(
            json.dumps(payload, default=str, sort_keys=True).encode()
        ).hexdigest()
        approval = store(
            c,
            "automation.approval",
            {
                "action_id": str(action["id"]),
                "payload_hash": digest,
                "action": payload,
                "expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            },
            "pending",
        )
        store(
            c,
            "automation.audit_event",
            {
                "action": "proposal_created",
                "action_id": str(action["id"]),
                "approval_id": str(approval["id"]),
            },
            "recorded",
        )
        return approval


class Decision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    version: int = Field(ge=1)


@app.post("/api/v1/approvals/{approval_id}/decision")
def decision(approval_id: UUID, body: Decision):
    with session() as c:
        found = rows(
            c,
            "SELECT * FROM automation.approval WHERE id=:id FOR UPDATE",
            {"id": approval_id},
        )
        if not found:
            raise HTTPException(404, "Approval not found.")
        approval = found[0]
        if approval["status"] != "pending" or body.version != approval["version"]:
            raise HTTPException(
                409, "This approval has changed. Refresh before deciding."
            )
        if datetime.fromisoformat(approval["payload"]["expires_at"]) < datetime.now(
            UTC
        ):
            raise HTTPException(409, "Approval expired.")
        action = rows(
            c,
            "SELECT * FROM automation.action WHERE id=:id FOR UPDATE",
            {"id": UUID(approval["payload"]["action_id"])},
        )[0]
        digest = hashlib.sha256(
            json.dumps(action["payload"], default=str, sort_keys=True).encode()
        ).hexdigest()
        if digest != approval["payload"]["payload_hash"]:
            raise HTTPException(
                409, "The action payload changed; a new approval is required."
            )
        status = "approved" if body.decision == "approve" else "rejected"
        c.execute(
            text(
                "UPDATE automation.approval SET status=:status,updated_at=now(),version=version+1 WHERE id=:id"
            ),
            {"status": status, "id": approval_id},
        )
        c.execute(
            text(
                "UPDATE automation.action SET status=:status,updated_at=now() WHERE id=:id"
            ),
            {"status": status, "id": action["id"]},
        )
        store(
            c,
            "automation.audit_event",
            {
                "approval_id": str(approval_id),
                "decision": status,
                "action_id": str(action["id"]),
            },
            "recorded",
        )
        return {
            "status": status,
            "action_id": action["id"],
            "execution": "Queued for the Temporal worker"
            if status == "approved"
            else "Rejected",
        }


class Rule(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    threshold: int = Field(default=30, ge=1, le=365)
    minimum_amount: Decimal = Field(default=10000, ge=0)
    operator: str = Field(default="AND", pattern="^(AND|OR)$")
    cooldown_hours: int = Field(default=24, ge=1, le=720)
    active: bool = False


@app.post("/api/v1/rules/simulate")
def simulate(body: Rule):
    with session() as c:
        return rows(
            c,
            f"SELECT id,name opportunity,amount,days_in_stage FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND (days_in_stage>=:days {body.operator} amount>=:amount) ORDER BY amount DESC LIMIT 30",
            {"days": body.threshold, "amount": body.minimum_amount},
        )


@app.post("/api/v1/rules", status_code=201)
def save_rule(body: Rule):
    with session() as c:
        return store(
            c,
            "automation.rule",
            {
                **body.model_dump(mode="json"),
                "trigger": "scheduled",
                "action": "internal_follow_up",
                "approval_required": True,
            },
            "active" if body.active else "draft",
        )


class Scenario(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    win_rate: float = Field(default=0, ge=-30, le=30)
    slippage: float = Field(default=0, ge=-30, le=30)
    deal_size: float = Field(default=0, ge=-30, le=30)
    churn: float = Field(default=0, ge=-30, le=30)
    expansion: float = Field(default=0, ge=-30, le=30)
    growth: float = Field(default=0, ge=-30, le=30)


@app.post("/api/v1/scenarios")
def scenario(body: Scenario):
    with session() as c:
        forecasts = rows(
            c,
            "SELECT payload FROM ml.prediction WHERE payload->>'kind'='forecast' ORDER BY payload->>'month'",
            {},
        )
        if not forecasts:
            raise HTTPException(
                409,
                "Train and register a revenue forecasting model before recalculating scenarios.",
            )
        # Explicit sensitivity assumptions, separate from probabilistic forecast intervals.
        multiplier = (
            (1 + body.growth / 100)
            * (1 + body.deal_size / 100)
            * (1 + body.win_rate / 100)
            * (1 - body.slippage / 100)
            * (1 - body.churn / 100)
            * (1 + body.expansion / 100)
        )
        values = [
            {
                **r["payload"],
                "scenario_value": round(float(r["payload"]["value"]) * multiplier, 2),
            }
            for r in forecasts
        ]
        return store(
            c,
            "planning.forecast_scenario",
            {
                **body.model_dump(),
                "values": values,
                "method": "Multiplicative sensitivity; not causal estimates or guaranteed outcomes.",
            },
        )


class Investigation(BaseModel):
    question: str = Field(min_length=5, max_length=2000)


@app.post("/api/v1/investigations")
async def investigate(body: Investigation):
    if not settings.llm_api_key or not settings.llm_model:
        raise HTTPException(
            503,
            "Configure an LLM provider and model to run evidence-grounded investigations. BI, reports and workflows remain available.",
        )
    from services.ai_analyst.orchestration import (
        ProviderUnavailableError,
    )
    from services.ai_analyst.orchestration import (
        investigate as run,
    )

    try:
        return await run(body.question)
    except ProviderUnavailableError as exc:
        raise HTTPException(
            429 if exc.code == "rate_limited" else 503,
            str(exc),
            headers={"Retry-After": str(exc.retry_seconds)},
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            503,
            "The AI provider took too long to complete this investigation. Please try a narrower question.",
        ) from exc
    except Exception as exc:
        log.exception("investigation_failed")
        raise HTTPException(
            502,
            "The provider investigation did not complete. No unapproved external action was executed.",
        ) from exc


@app.get("/api/v1/investigations/{conversation_id}")
def saved_investigation(conversation_id: UUID):
    with session() as conn:
        conversations = rows(
            conn,
            "SELECT id,status,payload,created_at FROM ai.conversation WHERE id=:id",
            {"id": conversation_id},
        )
        if not conversations:
            raise HTTPException(404, "Investigation not found.")
        messages = rows(
            conn,
            "SELECT payload FROM ai.message WHERE payload->>'conversation_id'=:id ORDER BY created_at",
            {"id": str(conversation_id)},
        )
        evidence = rows(
            conn,
            "SELECT id,payload FROM ai.evidence_reference WHERE payload->>'conversation_id'=:id ORDER BY created_at",
            {"id": str(conversation_id)},
        )
    conversation = conversations[0]
    answers = [
        m["payload"]["content"]
        for m in messages
        if m["payload"].get("role") == "assistant"
    ]
    return {
        "conversation_id": conversation_id,
        "status": conversation["status"],
        "answer": answers[-1]
        if answers
        else conversation["payload"].get(
            "failure_message", "This investigation has not completed."
        ),
        "evidence": [
            {
                "id": str(e["id"]),
                "tool": e["payload"].get("tool"),
                "data": e["payload"].get("result"),
            }
            for e in evidence
        ],
        "meta": conversation["payload"],
    }


class Report(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    start: date
    end: date
    segment: str = "All"
    metrics: list[str] = Field(default_factory=lambda: ["invoiced", "mrr", "pipeline"])


@app.post("/api/v1/reports", status_code=201)
def report(body: Report):
    begin, end = dates(body.start, body.end)
    with session() as c:
        snapshot = dashboard(c, "overview", begin, end, body.segment)
        chosen = [m for m in snapshot["metrics"] if m["id"] in body.metrics]
        if not chosen:
            raise HTTPException(422, "Select at least one available metric.")
        return store(
            c,
            "reporting.report",
            {
                "title": body.title,
                "start": str(body.start),
                "end": str(body.end),
                "segment": body.segment,
                "metrics": chosen,
                "basis": snapshot["meta"]["financial_basis"],
                "demo": True,
            },
            "generated",
        )


@app.get("/api/v1/reports/{report_id}/download")
def download_report(report_id: UUID, format: str = "csv"):
    with session() as c:
        report = rows(
            c, "SELECT * FROM reporting.report WHERE id=:id", {"id": report_id}
        )
    if not report:
        raise HTTPException(404, "Report not found.")
    payload = report[0]["payload"]
    if format == "pdf":
        from reportlab.pdfgen import canvas

        output = io.BytesIO()
        pdf = canvas.Canvas(output)
        pdf.setTitle(payload["title"])
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(48, 790, "RevPilot / Northstar Cloud")
        pdf.setFont("Helvetica", 11)
        for i, line in enumerate(
            [
                payload["title"],
                f"{payload['start']} to {payload['end']}",
                "Synthetic demonstration data / " + payload["basis"],
            ]
            + [
                f"{m['label']}: {float(m['value']):,.2f} {m['unit']}"
                for m in payload["metrics"]
                if m["value"] is not None
            ]
        ):
            pdf.drawString(48, 750 - i * 26, line)
        pdf.save()
        return Response(
            output.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="revpilot-report.pdf"'
            },
        )
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Metric", "Value", "Unit", "Definition", "Data mode"])
    for m in payload["metrics"]:
        writer.writerow(
            [
                m["label"],
                m["value"],
                m["unit"],
                m["definition"],
                "Synthetic demonstration",
            ]
        )
    return Response(
        stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="revpilot-report.csv"'},
    )


@app.get("/api/v1/export/{screen}")
def export(
    screen: str,
    start: date | None = None,
    end: date | None = None,
    segment: str = "All",
):
    if screen not in SCREENS:
        raise HTTPException(404)
    begin, finish = dates(start, end)
    with session() as c:
        if screen in ("pipeline", "recovery"):
            data = rows(
                c,
                "SELECT name,account,owner,stage,amount,expected_close,days_in_stage FROM mart.pipeline WHERE created_at<:end AND (:segment='All' OR segment=:segment) ORDER BY amount DESC",
                {"end": finish, "segment": segment},
            )
        elif screen == "customers":
            data = rows(
                c,
                "SELECT name,segment,region,acquired_at FROM core.account WHERE acquired_at<:end AND (:segment='All' OR segment=:segment) ORDER BY name",
                {"end": finish, "segment": segment},
            )
        else:
            data = dashboard(c, screen, begin, finish, segment)["metrics"]
    stream = io.StringIO()
    writer = csv.writer(stream)
    if data:
        writer.writerow(data[0].keys())
        for row in data:
            values = []
            for v in row.values():
                value = str(v) if v is not None else ""
                if value.startswith(
                    ("=", "+", "-", "@", "\t", "\r")
                ) and not isinstance(v, (int, float, Decimal)):
                    value = "'" + value
                values.append(value)
            writer.writerow(values)
    return Response(
        stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="revpilot-{screen}.csv"'
        },
    )


@app.post("/api/v1/imports/preview")
async def preview(file: Annotated[UploadFile, File()]):
    content = await file.read(2_000_001)
    if len(content) > 2_000_000:
        raise HTTPException(413, "Files must be at most 2 MB.")
    try:
        if file.filename and file.filename.lower().endswith(".xlsx"):
            from openpyxl import load_workbook

            workbook = load_workbook(
                io.BytesIO(content), read_only=True, data_only=True
            )
            values = list(workbook.active.values)
            headers = [str(v or "").strip() for v in values[0]]
            data = [dict(zip(headers, row)) for row in values[1:]]
        else:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            headers = reader.fieldnames or []
            data = list(reader)
        if not data or len(data) > 10000:
            raise ValueError("Upload between 1 and 10,000 data rows.")
        if len(headers) != len(set(headers)) or len(headers) > 50:
            raise ValueError("Provide unique column headings, at most 50 columns.")
    except Exception as exc:
        raise HTTPException(
            422, "The file could not be parsed as a supported CSV or Excel table."
        ) from exc
    with session() as c:
        batch = store(
            c,
            "raw.import_batch",
            {
                "filename": file.filename,
                "headers": headers,
                "rows": data,
                "row_count": len(data),
                "sha256": hashlib.sha256(content).hexdigest(),
            },
            "preview",
        )
    return {
        "id": batch["id"],
        "headers": headers,
        "preview": data[:10],
        "row_count": len(data),
        "supported_entities": ["accounts"],
    }


class ImportConfirmation(BaseModel):
    name_column: str
    segment_column: str
    region_column: str


@app.post("/api/v1/imports/{batch_id}/confirm")
def confirm_import(batch_id: UUID, body: ImportConfirmation):
    with session() as c:
        batch = rows(
            c,
            "SELECT * FROM raw.import_batch WHERE id=:id FOR UPDATE",
            {"id": batch_id},
        )
        if not batch:
            raise HTTPException(404)
        if batch[0]["status"] != "preview":
            raise HTTPException(409, "This import has already been handled.")
        data = batch[0]["payload"]
        owner = c.execute(
            text("SELECT id FROM core.sales_rep ORDER BY id LIMIT 1")
        ).scalar()
        seen = set()
        errors = []
        valid = []
        for i, r in enumerate(data["rows"], 2):
            name = str(r.get(body.name_column) or "").strip()
            segment = r.get(body.segment_column)
            region = str(r.get(body.region_column) or "").strip()
            if (
                not name
                or len(name) > 200
                or segment not in ("SMB", "Mid-market", "Enterprise")
                or not region
                or name.casefold() in seen
            ):
                errors.append(
                    {"row": i, "error": "Check name, segment, region and duplicates."}
                )
                continue
            seen.add(name.casefold())
            valid.append(
                {
                    "id": uuid4(),
                    "org_id": tenant.get(),
                    "name": name,
                    "segment": segment,
                    "region": region,
                    "owner_id": owner,
                    "acquired_at": datetime.now(UTC),
                }
            )
        if errors:
            raise HTTPException(
                422,
                {
                    "message": "Nothing imported; fix invalid rows and preview again.",
                    "errors": errors[:100],
                },
            )
        for row in valid:
            c.execute(
                text(
                    "INSERT INTO core.account(id,org_id,name,segment,region,owner_id,acquired_at) VALUES(:id,:org_id,:name,:segment,:region,:owner_id,:acquired_at)"
                ),
                row,
            )
        c.execute(
            text(
                "UPDATE raw.import_batch SET status='committed',payload=payload-'rows',updated_at=now() WHERE id=:id"
            ),
            {"id": batch_id},
        )
        store(
            c,
            "ops.job_run",
            {
                "name": "Account import",
                "inserted": len(valid),
                "batch_id": str(batch_id),
            },
            "success",
        )
        return {"inserted": len(valid), "status": "committed"}
