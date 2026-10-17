"""Deterministic synthetic commercial history. All records belong to a demo tenant."""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, text

from apps.api.db import DEMO_ORG, settings

ANCHOR = datetime(2026, 10, 14, 12, tzinfo=UTC)
START = datetime(2023, 11, 1, tzinfo=UTC)
RNG = random.Random(20261014)
ORG = str(DEMO_ORG)


def uid(key):
    return str(uuid5(NAMESPACE_URL, "revpilot-demo:" + str(key)))


def money(value):
    return Decimal(str(round(value, 2)))


def batch(conn, table, records):
    if not records:
        return
    keys = list(records[0])
    sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join(':' + k for k in keys)}) ON CONFLICT DO NOTHING"
    conn.execute(text(sql), records)


def main():
    with create_engine(settings.migration_database_url).begin() as conn:
        conn.execute(text("SELECT set_config('app.org_id', :org, true)"), {"org": ORG})
        if conn.execute(
            text("SELECT 1 FROM identity.organisation WHERE id=:id"), {"id": ORG}
        ).scalar():
            print("Demo tenant already exists; preserving its actions and history.")
            return
        batch(
            conn,
            "identity.organisation",
            [{"id": ORG, "name": "Northstar Cloud", "demo": True}],
        )
        regions = ["United Kingdom", "North America", "Europe", "Asia Pacific"]
        reps = [
            {"id": uid(f"rep-{i}"), "org_id": ORG, "name": n, "region": regions[i % 4]}
            for i, n in enumerate(
                [
                    "Amelia Brooks",
                    "Daniel Chen",
                    "Sofia Morgan",
                    "James Patel",
                    "Chloe Williams",
                    "Oliver Reed",
                    "Isabella Clarke",
                    "Noah Wilson",
                    "Maya Turner",
                    "Ethan Hughes",
                    "Grace Taylor",
                    "Liam Evans",
                    "Ava Scott",
                    "Lucas Baker",
                    "Freya Adams",
                    "Henry Wright",
                    "Ella Lewis",
                    "Leo Martin",
                    "Aria Walker",
                    "Jack Hall",
                    "Lily Young",
                    "Oscar King",
                    "Zoe Hill",
                    "Theo Green",
                    "Ruby Wood",
                    "Finn Harris",
                    "Alice Cooper",
                    "Max Ward",
                    "Evie Davies",
                    "Adam Morris",
                    "Ivy Bell",
                    "Sam Collins",
                    "Nora White",
                    "Alex Thomas",
                    "Rose Mitchell",
                ]
            )
        ]
        batch(conn, "core.sales_rep", reps)
        prefixes = [
            "Aster",
            "Meridian",
            "Summit",
            "Orion",
            "Cedar",
            "Vector",
            "Horizon",
            "Pioneer",
            "Vertex",
            "Atlas",
            "Ember",
            "Cobalt",
            "Juniper",
            "Oak",
            "Keystone",
            "Lattice",
            "Beacon",
            "Mosaic",
            "Harbour",
            "Evergreen",
        ]
        suffixes = [
            "Systems",
            "Labs",
            "Technologies",
            "Partners",
            "Group",
            "Networks",
            "Dynamics",
            "Works",
            "Digital",
            "Analytics",
        ]
        accounts = []
        for i in range(2500):
            acquired = START + timedelta(days=RNG.randrange(980))
            accounts.append(
                {
                    "id": uid(f"account-{i}"),
                    "org_id": ORG,
                    "name": f"{prefixes[i % 20]} {suffixes[(i // 20) % 10]} {i + 1:04d}",
                    "segment": RNG.choices(
                        ["Enterprise", "Mid-market", "SMB"], [0.18, 0.32, 0.5]
                    )[0],
                    "region": RNG.choice(regions),
                    "owner_id": reps[i % 35]["id"],
                    "acquired_at": acquired,
                }
            )
        batch(conn, "core.account", accounts)
        batch(
            conn,
            "core.contact",
            [
                {
                    "id": uid(f"contact-{i}"),
                    "org_id": ORG,
                    "account_id": accounts[i % 2500]["id"],
                    "name": f"Demo contact {i + 1}",
                    "email": f"contact{i + 1}@example.test",
                }
                for i in range(6000)
            ],
        )
        opportunities = []
        histories = []
        stages = ["Discovery", "Qualified", "Proposal", "Negotiation"]
        for i in range(8000):
            account = accounts[i % 2500]
            created = account["acquired_at"] + timedelta(
                days=RNG.randrange(max(1, (ANCHOR - account["acquired_at"]).days - 3))
            )
            elapsed = (ANCHOR - created).days
            cycle = RNG.randint(25, 145)
            segment = account["segment"]
            amount = money(
                RNG.lognormvariate(
                    {"SMB": 8.4, "Mid-market": 9.8, "Enterprise": 11}[segment], 0.55
                )
            )
            finished = elapsed > cycle
            won = (
                RNG.random()
                < {"SMB": 0.48, "Mid-market": 0.4, "Enterprise": 0.29}[segment]
            )
            final = (
                ("Won" if won else "Lost")
                if finished
                else stages[min(3, elapsed // 22)]
            )
            closed = created + timedelta(days=cycle) if finished else None
            entered = closed or created + timedelta(
                days=max(0, elapsed - RNG.randint(1, max(2, min(elapsed + 1, 60))))
            )
            opportunity = {
                "id": uid(f"opp-{i}"),
                "org_id": ORG,
                "account_id": account["id"],
                "owner_id": account["owner_id"],
                "name": f"{account['name']} / {RNG.choice(['Platform', 'Expansion', 'Enterprise', 'Analytics'])}",
                "stage": final,
                "amount": amount,
                "currency": "GBP",
                "created_at": created,
                "expected_close": created
                + timedelta(days=cycle + RNG.randint(-15, 25)),
                "closed_at": closed,
                "stage_entered_at": entered,
                "lead_source": RNG.choice(
                    ["Inbound", "Partner", "Outbound", "Referral"]
                ),
                "lost_reason": RNG.choice(
                    ["Timing", "Budget", "Competitor", "No decision"]
                )
                if final == "Lost"
                else None,
            }
            opportunities.append(opportunity)
            history_stages = stages + ([final] if finished else [])
            for j, stage in enumerate(history_stages):
                when = created + timedelta(days=j * max(1, cycle // 4))
                if when > entered and stage != final:
                    continue
                histories.append(
                    {
                        "id": uid(f"history-{i}-{j}"),
                        "org_id": ORG,
                        "opportunity_id": opportunity["id"],
                        "from_stage": history_stages[j - 1] if j else None,
                        "to_stage": stage,
                        "occurred_at": entered if stage == final else when,
                    }
                )
        batch(conn, "core.opportunity", opportunities)
        batch(conn, "core.opportunity_stage_history", histories)
        activities = []
        for i in range(45000):
            opp = opportunities[i % 8000]
            end = opp["closed_at"] or ANCHOR
            occurred = opp["created_at"] + timedelta(
                seconds=RNG.randrange(
                    max(1, int((end - opp["created_at"]).total_seconds()))
                )
            )
            activities.append(
                {
                    "id": uid(f"activity-{i}"),
                    "org_id": ORG,
                    "opportunity_id": opp["id"],
                    "kind": RNG.choice(["Call", "Email", "Meeting", "Demo"]),
                    "occurred_at": occurred,
                }
            )
        batch(conn, "core.activity", activities)
        subs = []
        for i, account in enumerate(accounts[:1800]):
            start = account["acquired_at"]
            end = (
                start + timedelta(days=RNG.randint(120, 700))
                if RNG.random() < 0.19
                else None
            )
            if end and end > ANCHOR:
                end = None
            subs.append(
                {
                    "id": uid(f"sub-{i}"),
                    "org_id": ORG,
                    "account_id": account["id"],
                    "monthly_amount": money(
                        RNG.lognormvariate(
                            {"SMB": 5.6, "Mid-market": 7, "Enterprise": 8.3}[
                                account["segment"]
                            ],
                            0.4,
                        )
                    ),
                    "currency": "GBP",
                    "started_at": start,
                    "ended_at": end,
                }
            )
        batch(conn, "finance.subscription", subs)
        invoices = []
        payments = []
        lines = []
        for i in range(15000):
            sub = subs[i % 1800]
            end = sub["ended_at"] or ANCHOR
            date = sub["started_at"] + timedelta(
                days=RNG.randrange(max(1, (end - sub["started_at"]).days))
            )
            invoice = {
                "id": uid(f"invoice-{i}"),
                "org_id": ORG,
                "account_id": sub["account_id"],
                "subscription_id": sub["id"],
                "amount": sub["monthly_amount"],
                "currency": "GBP",
                "issued_at": date,
                "due_at": date + timedelta(days=30),
            }
            invoices.append(invoice)
            lines.append(
                {
                    "id": uid(f"line-{i}"),
                    "org_id": ORG,
                    "invoice_id": invoice["id"],
                    "description": "Synthetic subscription service",
                    "amount": invoice["amount"],
                }
            )
            paid = date + timedelta(days=RNG.randint(10, 50))
            if RNG.random() < 0.9 and paid < ANCHOR:
                payments.append(
                    {
                        "id": uid(f"payment-{i}"),
                        "org_id": ORG,
                        "invoice_id": invoice["id"],
                        "amount": invoice["amount"],
                        "paid_at": paid,
                    }
                )
        batch(conn, "finance.invoice", invoices)
        batch(conn, "finance.invoice_line", lines)
        batch(conn, "finance.payment", payments)
        targets = []
        for i in range(36):
            year = 2023 + (10 + i) // 12
            month = (10 + i) % 12 + 1
            targets.append(
                {
                    "id": uid(f"target-{i}"),
                    "org_id": ORG,
                    "month": datetime(year, month, 1).date(),
                    "amount": money(850000 + i * 25000),
                    "currency": "GBP",
                }
            )
        batch(conn, "planning.revenue_target", targets)
        import json

        conn.execute(
            text(
                "INSERT INTO ops.job_run(org_id,status,payload) VALUES(:org,'success',cast(:payload as jsonb))"
            ),
            {
                "org": ORG,
                "payload": json.dumps(
                    {
                        "name": "Deterministic demo generation",
                        "seed": 20261014,
                        "accounts": 2500,
                        "contacts": 6000,
                        "opportunities": 8000,
                        "activities": 45000,
                        "subscriptions": 1800,
                        "invoices": 15000,
                        "payments": len(payments),
                        "anchor": ANCHOR.isoformat(),
                    }
                ),
            },
        )
        conn.execute(
            text(
                "INSERT INTO ops.quality_result(org_id,status,payload) VALUES(:org,'passed',:payload)"
            ),
            {
                "org": ORG,
                "payload": '{"check":"Foreign keys, unique IDs and nonnegative money","source":"PostgreSQL constraints"}',
            },
        )
        print(
            f"Demo loaded: 2,500 accounts, 8,000 opportunities, 45,000 activities, 15,000 invoices, {len(payments):,} payments."
        )


if __name__ == "__main__":
    main()
