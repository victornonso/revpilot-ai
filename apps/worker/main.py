"""Temporal worker plus resumable dispatch of database-persisted proposals."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

from apps.api.db import rows, session, settings
from apps.api.main import Proposal, propose, store
from services.automation.workflows import FollowUpWorkflow


@activity.defn
def approval_state(action_id: str) -> str:
    with session() as conn:
        found = rows(
            conn,
            "SELECT status,payload FROM automation.approval WHERE payload->>'action_id'=:id",
            {"id": action_id},
        )
        if not found:
            return "cancelled"
        row = found[0]
        if row["status"] == "pending" and datetime.fromisoformat(
            row["payload"]["expires_at"]
        ) < datetime.now(UTC):
            conn.execute(
                text(
                    "UPDATE automation.approval SET status='expired',updated_at=now() WHERE payload->>'action_id'=:id"
                ),
                {"id": action_id},
            )
            return "expired"
        return row["status"]


@activity.defn
def execute_demo_action(action_id: str) -> dict:
    with session() as conn:
        found = rows(
            conn,
            "SELECT * FROM automation.action WHERE id=:id FOR UPDATE",
            {"id": UUID(action_id)},
        )
        if not found:
            raise ValueError("Action not found")
        action = found[0]
        approvals = rows(
            conn,
            "SELECT * FROM automation.approval WHERE payload->>'action_id'=:id AND status='approved'",
            {"id": action_id},
        )
        if not approvals:
            raise ValueError("Exact action approval is required")
        import hashlib
        import json

        digest = hashlib.sha256(
            json.dumps(action["payload"], sort_keys=True, default=str).encode()
        ).hexdigest()
        if digest != approvals[0]["payload"]["payload_hash"]:
            raise ValueError("Action changed after approval")
        if action["payload"].get("adapter") != "isolated-demo":
            raise ValueError("No external execution adapter configured")
        execution = store(
            conn,
            "automation.execution",
            {
                "action_id": action_id,
                "title": action["payload"]["title"],
                "adapter": "isolated-demo",
                "outcome": "Internal follow-up recorded. No external communication was sent.",
                "orchestrator": "Temporal",
            },
            "executed",
            action_id,
        )
        conn.execute(
            text(
                "UPDATE automation.action SET status='executed',updated_at=now() WHERE id=:id"
            ),
            {"id": UUID(action_id)},
        )
        store(
            conn,
            "automation.audit_event",
            {
                "action_id": action_id,
                "execution_id": str(execution["id"]),
                "event": "demo_action_executed",
            },
            "recorded",
            f"executed:{action_id}",
        )
        return {
            "id": str(execution["id"]),
            "status": "executed",
            "adapter": "isolated-demo",
        }


async def dispatch(client):
    while True:
        try:
            with session() as conn:
                pending = rows(
                    conn,
                    "SELECT id FROM automation.action WHERE status IN ('pending','approved') ORDER BY created_at LIMIT 100",
                )
                rules = rows(
                    conn, "SELECT * FROM automation.rule WHERE status='active'"
                )
            for row in pending:
                try:
                    await client.start_workflow(
                        FollowUpWorkflow.run,
                        str(row["id"]),
                        id="follow-up-" + str(row["id"]),
                        task_queue="revpilot-actions",
                    )
                except WorkflowAlreadyStartedError:
                    pass
            for rule in rules:
                definition = rule["payload"]
                operator = "OR" if definition.get("operator") == "OR" else "AND"
                with session() as conn:
                    candidates = rows(
                        conn,
                        f"SELECT id,name FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND (days_in_stage>=:days {operator} amount>=:amount) AND NOT EXISTS(SELECT 1 FROM automation.action a WHERE a.payload->'opportunity'->>'id'=mart.pipeline.id::text AND a.created_at>now()-make_interval(hours=>:cooldown)) ORDER BY amount DESC LIMIT 5",
                        {
                            "days": definition["threshold"],
                            "amount": definition["minimum_amount"],
                            "cooldown": definition.get("cooldown_hours", 24),
                        },
                    )
                for candidate in candidates:
                    propose(
                        Proposal(
                            opportunity_id=candidate["id"],
                            title=definition["title"],
                            note=f"Rule {rule['id']} / version {rule['version']}",
                        )
                    )
        except Exception:
            import logging

            logging.getLogger(__name__).exception("dispatch_failed")
        await asyncio.sleep(5)


async def main():
    client = await Client.connect(settings.temporal_address)
    async with Worker(
        client,
        task_queue="revpilot-actions",
        workflows=[FollowUpWorkflow],
        activities=[approval_state, execute_demo_action],
        activity_executor=ThreadPoolExecutor(max_workers=4),
    ):
        await dispatch(client)


if __name__ == "__main__":
    asyncio.run(main())
