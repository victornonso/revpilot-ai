"""Governed SQL analytics. No browser computes commercial KPIs."""

from datetime import UTC, datetime

from sqlalchemy import text

from .db import rows

CATALOGUE = {
    "invoiced": (
        "Invoiced revenue",
        "GBP",
        "Sum of invoice face amounts issued in the reporting period; not cash or recognised revenue.",
    ),
    "cash": (
        "Cash collected",
        "GBP",
        "Sum of payments recorded in the reporting period.",
    ),
    "mrr": (
        "MRR",
        "GBP/month",
        "Monthly subscription amounts active at the end of the reporting period.",
    ),
    "arr": (
        "ARR",
        "GBP/year",
        "Twelve times end-of-period MRR; annualised run rate, not recognised revenue.",
    ),
    "pipeline": (
        "Open pipeline",
        "GBP",
        "Open opportunities created before period end; a current-state view, not a historical snapshot.",
    ),
    "weighted": (
        "Stage-weighted pipeline",
        "GBP",
        "Open amount times documented stage heuristic: 15%, 35%, 55%, 75%. Not a calibrated ML probability.",
    ),
    "win_rate": (
        "Win rate",
        "%",
        "Won divided by Won plus Lost opportunities closed in the period.",
    ),
    "sales_cycle": (
        "Sales cycle",
        "days",
        "Mean creation-to-close duration of won opportunities in the period.",
    ),
    "active": (
        "Active customers",
        "accounts",
        "Distinct accounts with a subscription active at period end.",
    ),
    "churn": (
        "Logo churn",
        "%",
        "Accounts active at period start with no active subscription at period end, divided by starting active accounts.",
    ),
    "overdue": (
        "Overdue balance",
        "GBP",
        "Positive unpaid invoice balances with due date before period end; a current payment-state balance.",
    ),
    "at_risk": (
        "Stalled pipeline",
        "GBP",
        "Open opportunities with more than 30 days in their present stage.",
    ),
}


def metric(key, value, unit=None, note=None):
    title, default, definition = CATALOGUE.get(
        key, (key.replace("_", " ").title(), "count", "Operational record count.")
    )
    return {
        "id": key,
        "label": title,
        "value": value,
        "unit": unit or default,
        "definition": note or definition,
    }


def query(conn, sql, p):
    return rows(conn, sql, p)


def scalar(conn, sql, p):
    return conn.execute(text(sql), p).scalar()


def chart(conn, title, sql, p, kind="bar", unit="GBP", span=1):
    return {
        "title": title,
        "kind": kind,
        "unit": unit,
        "span": span,
        "rows": query(conn, sql, p),
    }


def dashboard(
    conn,
    screen,
    start,
    end,
    segment,
    search="",
    sort="amount",
    direction="desc",
    page=1,
    stage="All",
    owner="All",
):
    p = {
        "start": start,
        "end": end,
        "segment": segment,
        "search": f"%{search}%",
        "stage": stage,
        "owner": owner,
        "limit": 20,
        "offset": (page - 1) * 20,
    }
    period = "issued_at>=:start AND issued_at<:end"
    scope = "(:segment='All' OR a.segment=:segment)"
    pipeline_scope = "(:segment='All' OR segment=:segment)"
    revenue = scalar(
        conn,
        f"SELECT coalesce(sum(i.amount),0) FROM finance.invoice i JOIN core.account a ON a.id=i.account_id AND a.org_id=i.org_id WHERE {period} AND {scope}",
        p,
    )
    mrr = scalar(
        conn,
        f"SELECT coalesce(sum(s.monthly_amount),0) FROM finance.subscription s JOIN core.account a ON a.id=s.account_id AND a.org_id=s.org_id WHERE s.started_at<:end AND (s.ended_at IS NULL OR s.ended_at>=:end) AND {scope}",
        p,
    )
    pipe = scalar(
        conn,
        f"SELECT coalesce(sum(amount),0) FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND created_at<:end AND {pipeline_scope}",
        p,
    )
    weighted = scalar(
        conn,
        f"SELECT coalesce(sum(amount*stage_weight),0) FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND created_at<:end AND {pipeline_scope}",
        p,
    )
    risk = scalar(
        conn,
        f"SELECT coalesce(sum(amount),0) FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND days_in_stage>30 AND created_at<:end AND {pipeline_scope}",
        p,
    )
    trend = lambda title="Invoiced revenue vs target": chart(
        conn,
        title,
        """WITH cal AS (SELECT generate_series(date_trunc('month',cast(:start as timestamptz)),date_trunc('month',cast(:end as timestamptz)-interval '1 day'),interval '1 month')::date AS month), rev AS (SELECT date_trunc('month',i.issued_at)::date AS month,sum(i.amount) value FROM finance.invoice i JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id) WHERE i.issued_at>=:start AND i.issued_at<:end AND (:segment='All' OR a.segment=:segment) GROUP BY 1) SELECT to_char(c.month,'Mon YY') name,coalesce(r.value,0) value,t.amount target FROM cal c LEFT JOIN rev r USING(month) LEFT JOIN planning.revenue_target t USING(month) ORDER BY c.month""",
        p,
        "line",
        "GBP",
        2,
    )
    segment_chart = lambda: chart(
        conn,
        "Revenue by segment",
        f"SELECT a.segment name,sum(i.amount) value FROM finance.invoice i JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id) WHERE {period} AND {scope} GROUP BY 1 ORDER BY 2 DESC",
        p,
        "donut",
    )
    region_chart = lambda: chart(
        conn,
        "Revenue by region",
        f"SELECT a.region name,sum(i.amount) value FROM finance.invoice i JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id) WHERE {period} AND {scope} GROUP BY 1 ORDER BY 2 DESC",
        p,
    )
    stage_chart = lambda: chart(
        conn,
        "Pipeline by stage",
        f"SELECT stage name,sum(amount) value FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND created_at<:end AND {pipeline_scope} GROUP BY stage,stage_weight ORDER BY stage_weight",
        p,
        "bar",
    )
    target = scalar(
        conn,
        "SELECT coalesce(sum(amount),0) FROM planning.revenue_target WHERE month>=date_trunc('month',cast(:start as timestamptz)) AND month<:end",
        p,
    )
    result = {
        "metrics": [],
        "charts": [],
        "table": [],
        "total": 0,
        "page": page,
        "insights": [],
        "meta": {
            "demo": True,
            "organisation": "Northstar Cloud",
            "period": {"start": start, "end": end},
            "segment": segment,
            "generated_at": datetime.now(UTC),
            "source": "PostgreSQL analytical views",
            "financial_basis": "Invoiced revenue · GBP",
            "stale": False,
        },
    }
    organisation = query(conn, "SELECT name,demo FROM identity.organisation", {})
    if organisation:
        result["meta"].update(
            {"organisation": organisation[0]["name"], "demo": organisation[0]["demo"]}
        )
    latest = scalar(
        conn, "SELECT max(created_at) FROM ops.job_run WHERE status='success'", {}
    )
    result["meta"]["refreshed_at"] = latest
    result["meta"]["stale"] = bool(
        not result["meta"]["demo"]
        and latest
        and (datetime.now(UTC) - latest).total_seconds() > 86400
    )
    if screen == "overview":
        cash = scalar(
            conn,
            f"SELECT coalesce(sum(p.amount),0) FROM finance.payment p JOIN finance.invoice i ON (i.org_id,i.id)=(p.org_id,p.invoice_id) JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id) WHERE p.paid_at>=:start AND p.paid_at<:end AND {scope}",
            p,
        )
        result["metrics"] = [
            metric("invoiced", revenue),
            metric("cash", cash),
            metric(
                "target_attainment",
                revenue / target * 100 if target and segment == "All" else None,
                "%",
                "Invoiced revenue divided by the all-company period target. Segment targets are unavailable.",
            ),
            metric("arr", mrr * 12),
            metric("mrr", mrr),
            metric("pipeline", pipe),
            metric("weighted", weighted),
            metric("at_risk", risk),
        ]
        result["charts"] = [
            trend(),
            segment_chart(),
            stage_chart(),
            region_chart(),
            chart(
                conn,
                "Subscription starts and endings",
                "SELECT to_char(date_trunc('month',started_at),'Mon YY') name,count(*) value,count(*) FILTER(WHERE ended_at IS NOT NULL) churned FROM finance.subscription WHERE started_at>=:start AND started_at<:end GROUP BY date_trunc('month',started_at) ORDER BY date_trunc('month',started_at)",
                p,
                "line",
                "accounts",
            ),
        ]
        result["insights"] = [
            {
                "title": "Review stalled opportunities",
                "detail": f"{risk:,.2f} GBP remains in open opportunities aged over 30 days in stage.",
                "route": "recovery",
            },
            {
                "title": "Revenue has an explicit basis",
                "detail": "Invoiced revenue, cash collection and annualised recurring revenue are separate measures.",
                "route": "reports",
            },
        ]
    elif screen == "pipeline":
        stats = query(
            conn,
            f"SELECT count(*) FILTER(WHERE stage='Won')::numeric/nullif(count(*) FILTER(WHERE stage IN ('Won','Lost')),0)*100 win_rate,avg(extract(epoch from closed_at-created_at)/86400) FILTER(WHERE stage='Won') cycle FROM mart.pipeline WHERE closed_at>=:start AND closed_at<:end AND {pipeline_scope}",
            p,
        )[0]
        result["metrics"] = [
            metric("pipeline", pipe),
            metric("weighted", weighted),
            metric("win_rate", stats["win_rate"]),
            metric("sales_cycle", stats["cycle"]),
            metric("at_risk", risk),
        ]
        result["charts"] = [
            stage_chart(),
            chart(
                conn,
                "Time in current stage",
                f"SELECT stage name,avg(days_in_stage) value FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND {pipeline_scope} GROUP BY 1",
                p,
                "bar",
                "days",
            ),
            chart(
                conn,
                "Closed deal movement",
                f"SELECT to_char(date_trunc('month',closed_at),'Mon YY') name,sum(amount) FILTER(WHERE stage='Won') value,sum(amount) FILTER(WHERE stage='Lost') lost FROM mart.pipeline WHERE closed_at>=:start AND closed_at<:end AND {pipeline_scope} GROUP BY date_trunc('month',closed_at) ORDER BY date_trunc('month',closed_at)",
                p,
                "line",
            ),
            chart(
                conn,
                "Sales representative contribution",
                f"SELECT owner name,sum(amount) value FROM mart.pipeline WHERE stage='Won' AND closed_at>=:start AND closed_at<:end AND {pipeline_scope} GROUP BY 1 ORDER BY 2 DESC LIMIT 8",
                p,
            ),
        ]
        allowed = {
            "amount": "amount",
            "account": "account",
            "stage": "stage",
            "days_in_stage": "days_in_stage",
            "expected_close": "expected_close",
        }
        order = allowed.get(sort, "amount")
        way = "ASC" if direction == "asc" else "DESC"
        where = f"created_at<:end AND {pipeline_scope} AND (name ILIKE :search OR account ILIKE :search) AND (:stage='All' OR stage=:stage) AND (:owner='All' OR owner_id::text=:owner)"
        result["table"] = query(
            conn,
            f"SELECT id,name opportunity,account,owner,stage,amount,expected_close,days_in_stage,stage_weight*100 stage_weight_percent,CASE WHEN days_in_stage>30 AND stage NOT IN ('Won','Lost') THEN 'Stalled' WHEN stage IN ('Won','Lost') THEN stage ELSE 'On track' END risk FROM mart.pipeline WHERE {where} ORDER BY {order} {way},id LIMIT :limit OFFSET :offset",
            p,
        )
        result["total"] = scalar(
            conn, f"SELECT count(*) FROM mart.pipeline WHERE {where}", p
        )
        result["charts"].append(
            chart(
                conn,
                "Opportunity risk matrix",
                """SELECT id,name,days_in_stage age,amount value
          FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND created_at<:end
          AND (:segment='All' OR segment=:segment) ORDER BY amount DESC LIMIT 200""",
                p,
                "scatter",
                "GBP",
            )
        )
        result["charts"].append(
            chart(
                conn,
                "Stage-entry cohort progression",
                """SELECT h.to_stage name,count(DISTINCT h.opportunity_id) value
          FROM core.opportunity_stage_history h JOIN mart.pipeline o ON (o.org_id,o.id)=(h.org_id,h.opportunity_id)
          WHERE o.created_at>=:start AND o.created_at<:end AND h.occurred_at<:end
          AND h.to_stage!='Lost' AND (:segment='All' OR o.segment=:segment)
          GROUP BY h.to_stage ORDER BY array_position(ARRAY['Discovery','Qualified','Proposal','Negotiation','Won'],h.to_stage)""",
                p,
                "bar",
                "opportunities",
            )
        )
        result["owners"] = query(
            conn, "SELECT id,name FROM core.sales_rep ORDER BY name", {}
        )
    elif screen == "customers":
        active = scalar(
            conn,
            f"SELECT count(DISTINCT s.account_id) FROM finance.subscription s JOIN core.account a ON (a.org_id,a.id)=(s.org_id,s.account_id) WHERE s.started_at<:end AND (s.ended_at IS NULL OR s.ended_at>=:end) AND {scope}",
            p,
        )
        result["metrics"] = [
            metric("active", active),
            metric("mrr", mrr),
            metric("arr", mrr * 12),
            metric(
                "new_customers",
                scalar(
                    conn,
                    "SELECT count(*) FROM core.account WHERE acquired_at>=:start AND acquired_at<:end",
                    p,
                ),
                "accounts",
            ),
        ]
        result["charts"] = [
            chart(
                conn,
                "Customer acquisition by month",
                "SELECT to_char(date_trunc('month',acquired_at),'Mon YY') name,count(*) value FROM core.account WHERE acquired_at>=:start AND acquired_at<:end GROUP BY date_trunc('month',acquired_at) ORDER BY date_trunc('month',acquired_at)",
                p,
                "line",
                "accounts",
            ),
            segment_chart(),
            chart(
                conn,
                "Recurring revenue by segment",
                f"SELECT a.segment name,sum(s.monthly_amount) value FROM finance.subscription s JOIN core.account a ON (a.org_id,a.id)=(s.org_id,s.account_id) WHERE s.started_at<:end AND (s.ended_at IS NULL OR s.ended_at>=:end) AND {scope} GROUP BY 1",
                p,
            ),
            chart(
                conn,
                "Revenue concentration / top accounts",
                f"SELECT a.name name,sum(i.amount) value FROM finance.invoice i JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id) WHERE {period} AND {scope} GROUP BY a.id,a.name ORDER BY 2 DESC LIMIT 8",
                p,
            ),
        ]
        where = f"{scope} AND a.name ILIKE :search"
        result["table"] = query(
            conn,
            f"SELECT a.id,a.name account,a.segment,a.region,r.name owner,a.acquired_at,coalesce(sum(s.monthly_amount) FILTER(WHERE s.started_at<:end AND (s.ended_at IS NULL OR s.ended_at>=:end)),0) mrr FROM core.account a JOIN core.sales_rep r ON (r.org_id,r.id)=(a.org_id,a.owner_id) LEFT JOIN finance.subscription s ON (s.org_id,s.account_id)=(a.org_id,a.id) WHERE {where} GROUP BY a.id,a.name,a.segment,a.region,r.name,a.acquired_at ORDER BY mrr DESC,a.id LIMIT :limit OFFSET :offset",
            p,
        )
        result["total"] = scalar(
            conn, f"SELECT count(*) FROM core.account a WHERE {where}", p
        )
        retention = query(
            conn,
            """WITH balances AS (
          SELECT s.account_id,
          sum(s.monthly_amount) FILTER(WHERE s.started_at<:start AND (s.ended_at IS NULL OR s.ended_at>=:start)) start_mrr,
          sum(s.monthly_amount) FILTER(WHERE s.started_at<:start AND (s.ended_at IS NULL OR s.ended_at>=:end)) end_mrr
          FROM finance.subscription s JOIN core.account a ON (a.org_id,a.id)=(s.org_id,s.account_id)
          WHERE (:segment='All' OR a.segment=:segment) GROUP BY s.account_id
        ) SELECT count(*) FILTER(WHERE start_mrr>0) starting_accounts,
          100.0*count(*) FILTER(WHERE start_mrr>0 AND coalesce(end_mrr,0)>0)/nullif(count(*) FILTER(WHERE start_mrr>0),0) retention_percent,
          100.0*count(*) FILTER(WHERE start_mrr>0 AND coalesce(end_mrr,0)=0)/nullif(count(*) FILTER(WHERE start_mrr>0),0) churn_percent,
          100.0*sum(coalesce(end_mrr,0)) FILTER(WHERE start_mrr>0)/nullif(sum(start_mrr),0) nrr,
          100.0*sum(least(coalesce(end_mrr,0),start_mrr)) FILTER(WHERE start_mrr>0)/nullif(sum(start_mrr),0) grr
        FROM balances""",
            p,
        )[0]
        result["metrics"].extend(
            [
                metric(
                    "retention",
                    retention["retention_percent"],
                    "%",
                    "Starting active accounts still subscribed at period end divided by starting active accounts.",
                ),
                metric("churn", retention["churn_percent"]),
                metric(
                    "nrr",
                    retention["nrr"],
                    "%",
                    "End-period MRR from the starting customer cohort divided by its starting MRR. Prices are fixed in this demonstration history.",
                ),
                metric(
                    "grr",
                    retention["grr"],
                    "%",
                    "Starting-cohort retained MRR, capped at its original MRR, divided by starting MRR. Fixed-price demo history.",
                ),
            ]
        )
        result["charts"].insert(
            0,
            chart(
                conn,
                "Customer cohort retention",
                """SELECT to_char(cohort,'Mon YY') name,months_since_start period,
          100.0*sum(retained_accounts)/nullif(sum(starting_accounts),0) value
          FROM mart.subscription_cohorts WHERE cohort>=date_trunc('month',cast(:start as timestamptz))
          AND cohort<:end AND (:segment='All' OR segment=:segment)
          GROUP BY cohort,months_since_start ORDER BY cohort,months_since_start""",
                p,
                "heatmap",
                "%",
            ),
        )
    elif screen == "recovery":
        overdue = scalar(
            conn,
            "SELECT coalesce(sum(outstanding),0) FROM mart.invoice_balance WHERE due_at<:end AND outstanding>0",
            p,
        )
        result["metrics"] = [
            metric("at_risk", risk),
            metric("overdue", overdue),
            metric(
                "pending_interventions",
                scalar(
                    conn,
                    "SELECT count(*) FROM automation.action WHERE status='pending'",
                    {},
                ),
            ),
        ]
        result["charts"] = [
            chart(
                conn,
                "Stalled exposure by segment",
                "SELECT segment name,sum(amount) value FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND days_in_stage>30 GROUP BY 1",
                p,
            ),
            chart(
                conn,
                "Overdue balances by region",
                "SELECT a.region name,sum(i.outstanding) value FROM mart.invoice_balance i JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id) WHERE i.outstanding>0 AND i.due_at<:end GROUP BY 1",
                p,
            ),
        ]
        result["table"] = query(
            conn,
            f"SELECT id,name opportunity,account,owner,amount,days_in_stage,round(amount*least(days_in_stage,90)/90,2) priority_score FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND days_in_stage>30 AND {pipeline_scope} AND name ILIKE :search ORDER BY priority_score DESC,id LIMIT :limit OFFSET :offset",
            p,
        )
        result["total"] = scalar(
            conn,
            f"SELECT count(*) FROM mart.pipeline WHERE stage NOT IN ('Won','Lost') AND days_in_stage>30 AND {pipeline_scope} AND name ILIKE :search",
            p,
        )
    elif screen == "forecasting":
        result["charts"] = [trend("Historical invoiced revenue")]
        result["models"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM ml.model_version ORDER BY created_at DESC",
            {},
        )
        result["forecasts"] = query(
            conn,
            "SELECT payload FROM ml.prediction WHERE payload->>'kind'='forecast' ORDER BY payload->>'month'",
            {},
        )
        result["scenarios"] = query(
            conn,
            "SELECT id,payload,created_at FROM planning.forecast_scenario ORDER BY created_at DESC",
            {},
        )
        if result["forecasts"]:
            forecast_rows = [
                {
                    "name": r["payload"]["month"],
                    "value": r["payload"]["value"],
                    "lower": r["payload"]["lower"],
                    "upper": r["payload"]["upper"],
                }
                for r in result["forecasts"]
            ]
            result["charts"].append(
                {
                    "title": "Registered revenue forecast and empirical range",
                    "kind": "line",
                    "unit": "GBP",
                    "span": 1,
                    "rows": forecast_rows,
                }
            )
            result["metrics"] = [
                metric(
                    "forecast_revenue",
                    sum(r["value"] for r in forecast_rows),
                    "GBP",
                    "Sum of the three registered monthly invoiced-revenue forecasts.",
                ),
                metric(
                    "forecast_lower",
                    sum(r["lower"] for r in forecast_rows),
                    "GBP",
                    "Sum of monthly lower bounds; not a calibrated joint interval.",
                ),
                metric(
                    "forecast_upper",
                    sum(r["upper"] for r in forecast_rows),
                    "GBP",
                    "Sum of monthly upper bounds; not a calibrated joint interval.",
                ),
            ]
        evaluation = query(
            conn,
            "SELECT payload FROM ml.evaluation_run WHERE payload->>'kind'='forecast' ORDER BY created_at DESC LIMIT 1",
            {},
        )
        if evaluation:
            chosen = evaluation[0]["payload"]["name"]
            backtests = [
                r for r in evaluation[0]["payload"]["backtests"] if r["model"] == chosen
            ]
            result["charts"].append(
                {
                    "title": "Rolling-origin forecast evaluation",
                    "kind": "line",
                    "unit": "GBP",
                    "span": 1,
                    "rows": [
                        {
                            "name": r["month"],
                            "value": r["actual"],
                            "forecast": r["forecast"],
                        }
                        for r in backtests
                    ],
                }
            )
        for scenario in result["scenarios"][:2]:
            result["charts"].append(
                {
                    "title": scenario["payload"]["title"] + " / sensitivity",
                    "kind": "line",
                    "unit": "GBP",
                    "span": 1,
                    "rows": [
                        {
                            "name": r["month"],
                            "value": r["scenario_value"],
                            "baseline": r["value"],
                        }
                        for r in scenario["payload"]["values"]
                    ],
                }
            )
    elif screen == "automations":
        result["rules"] = query(
            conn,
            "SELECT id,status,payload,version,created_at FROM automation.rule ORDER BY created_at DESC",
            {},
        )
        result["approvals"] = query(
            conn,
            "SELECT id,status,payload,version,created_at FROM automation.approval ORDER BY created_at DESC LIMIT 100",
            {},
        )
        result["table"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM automation.execution ORDER BY created_at DESC LIMIT 20",
            {},
        )
        result["metrics"] = [
            metric(
                "active_rules", sum(r["status"] == "active" for r in result["rules"])
            ),
            metric(
                "pending_approvals",
                sum(r["status"] == "pending" for r in result["approvals"]),
            ),
            metric(
                "executions",
                scalar(conn, "SELECT count(*) FROM automation.execution", {}),
            ),
        ]
    elif screen == "reports":
        result["table"] = query(
            conn,
            "SELECT id,payload->>'title' report,status,version,created_at FROM reporting.report ORDER BY created_at DESC",
            {},
        )
        result["views"] = query(
            conn,
            "SELECT id,payload,created_at FROM reporting.saved_view ORDER BY created_at DESC",
            {},
        )
        result["schedules"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM reporting.schedule ORDER BY created_at DESC",
            {},
        )
    elif screen == "operations":
        result["jobs"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM ops.job_run ORDER BY created_at DESC LIMIT 50",
            {},
        )
        result["quality"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM ops.quality_result ORDER BY created_at DESC LIMIT 50",
            {},
        )
        result["models"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM ml.model_version ORDER BY created_at DESC",
            {},
        )
        result["imports"] = query(
            conn,
            "SELECT id,status,payload,created_at FROM raw.import_batch ORDER BY created_at DESC LIMIT 50",
            {},
        )
        result["integrations"] = query(
            conn, "SELECT id,status,payload,updated_at FROM integration.connection", {}
        )
        result["table"] = result["jobs"]
        result["metrics"] = [
            metric("jobs", len(result["jobs"])),
            metric("quality_checks", len(result["quality"])),
            metric("model_versions", len(result["models"])),
            metric("imports", len(result["imports"])),
        ]
    elif screen == "analyst":
        from .auth import role, visitor_scope
        from .db import settings

        private_access = not settings.public_demo_mode or role.get() == "demo_owner"
        result["private_owner_session"] = settings.public_demo_mode and private_access
        result["private_access_required"] = (
            settings.public_demo_mode
            and not private_access
            and not settings.public_analyst_enabled
        )
        result["configured"] = bool(
            __import__("apps.api.db", fromlist=["settings"]).settings.llm_api_key
        ) and (private_access or settings.public_analyst_enabled)
        result["conversations"] = (
            query(
                conn,
                "SELECT id,status,payload,created_at FROM ai.conversation WHERE (:scope='' AND coalesce(payload->>'visitor_scope','')='') OR payload->>'visitor_scope'=:scope ORDER BY created_at DESC LIMIT 30",
                {"scope": visitor_scope.get()},
            )
            if private_access or settings.public_analyst_enabled
            else []
        )
        result["catalogue"] = [
            {"id": key, "label": v[0], "unit": v[1], "definition": v[2]}
            for key, v in CATALOGUE.items()
        ]
    return result
