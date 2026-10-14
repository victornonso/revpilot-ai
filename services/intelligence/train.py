"""Measured synthetic-data benchmarks; time-ordered selection and persisted scoring."""

import json
import warnings
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import text
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from apps.api.db import ROOT, rows, session
from apps.api.main import store

warnings.filterwarnings("ignore", category=UserWarning)
ARTIFACTS = ROOT / ".local/models"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def classification(kind, records, features, categoricals):
    frame = pd.DataFrame(records).sort_values("snapshot_at")
    train = frame[frame.snapshot_at < pd.Timestamp("2025-01-01", tz="UTC")]
    validation = frame[
        (frame.snapshot_at >= pd.Timestamp("2025-01-01", tz="UTC"))
        & (frame.snapshot_at < pd.Timestamp("2026-01-01", tz="UTC"))
    ]
    test = frame[frame.snapshot_at >= pd.Timestamp("2026-01-01", tz="UTC")]
    if any(len(f) < 30 or f.target.nunique() < 2 for f in [train, validation, test]):
        raise RuntimeError(f"Insufficient time-separated labels for {kind}")
    numeric = [f for f in features if f not in categoricals]

    def pipeline(model):
        return make_pipeline(
            ColumnTransformer(
                [
                    (
                        "categories",
                        OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        categoricals,
                    ),
                    ("numbers", StandardScaler(), numeric),
                ]
            ),
            model,
        )

    candidates = {
        "Logistic regression": LogisticRegression(max_iter=1000, random_state=42),
        "LightGBM": LGBMClassifier(
            n_estimators=80,
            max_depth=4,
            num_leaves=12,
            verbosity=-1,
            random_state=42,
            n_jobs=2,
        ),
    }
    scores = {}
    for name, model in candidates.items():
        pipe = pipeline(model)
        pipe.fit(train[features], train.target)
        scores[name] = brier_score_loss(
            validation.target, pipe.predict_proba(validation[features])[:, 1]
        )
    winner = min(scores, key=scores.get)
    pipe = pipeline(candidates[winner])
    development = pd.concat([train, validation])
    pipe.fit(development[features], development.target)
    prediction = pipe.predict_proba(test[features])[:, 1]
    bins = pd.DataFrame({"probability": prediction, "target": test.target.values})
    bins["bin"] = pd.cut(
        bins.probability, bins=np.linspace(0, 1, 11), include_lowest=True
    )
    calibration = [
        {
            "bin": str(index),
            "mean_probability": float(group.probability.mean()),
            "observed_rate": float(group.target.mean()),
            "rows": len(group),
        }
        for index, group in bins.groupby("bin", observed=True)
    ]
    metrics = {
        "pr_auc": float(average_precision_score(test.target, prediction)),
        "roc_auc": float(roc_auc_score(test.target, prediction)),
        "brier": float(brier_score_loss(test.target, prediction)),
    }
    report = {
        "kind": kind,
        "name": winner,
        "features": features,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "train_end": "2024-12-31",
        "validation_end": "2025-12-31",
        "test_start": "2026-01-01",
        "selection": "Lowest validation Brier score",
        "validation_brier": scores,
        "metrics": metrics,
        "calibration": calibration,
        "scope": "Synthetic demonstration benchmark; not evidence of real-company performance.",
        "snapshot": "30 days after opportunity creation"
        if kind == "deal_win"
        else "90 days after subscription start",
        "trained_at": datetime.now(UTC).isoformat(),
    }
    joblib.dump(pipe, ARTIFACTS / f"{kind}.joblib")
    with session() as conn:
        version = store(conn, "ml.model_version", report, "registered")
        store(
            conn,
            "ml.evaluation_run",
            {"model_id": str(version["id"]), **report},
            "passed",
        )
        for row, prob in zip(test.to_dict("records"), prediction):
            store(
                conn,
                "ml.prediction",
                {
                    "kind": kind,
                    "entity_id": str(row["id"]),
                    "as_of": str(row["snapshot_at"]),
                    "probability": float(prob),
                    "target": int(row["target"]),
                    "model_id": str(version["id"]),
                    "scope": "held-out synthetic observations",
                },
                "scored",
                f"{kind}:{version['id']}:{row['id']}",
            )
    print(kind, winner, json.dumps(metrics))


def forecasts():
    with session() as conn:
        records = rows(
            conn,
            "SELECT date_trunc('month',issued_at)::date AS month,sum(amount)::float value FROM finance.invoice WHERE issued_at<date_trunc('month',now()) GROUP BY 1 ORDER BY 1",
        )
    frame = pd.DataFrame(records)
    y = frame.value.to_numpy()
    backtests = []

    def predict(values, kind, horizon=1):
        if kind == "Seasonal naive":
            return np.array([values[-12 + (h % 12)] for h in range(horizon)])
        if kind == "Exponential smoothing":
            return np.asarray(
                ExponentialSmoothing(
                    values, trend="add", seasonal="add", seasonal_periods=12
                )
                .fit(optimized=True)
                .forecast(horizon)
            )
        X = []
        target = []
        for i in range(12, len(values)):
            X.append([values[i - 1], values[i - 12], i % 12, i])
            target.append(values[i])
        model = HistGradientBoostingRegressor(
            max_iter=60, min_samples_leaf=3, max_leaf_nodes=5, random_state=42
        ).fit(X, target)
        history = list(values)
        out = []
        for h in range(horizon):
            i = len(history)
            value = float(model.predict([[history[-1], history[-12], i % 12, i]])[0])
            out.append(value)
            history.append(value)
        return np.array(out)

    candidates = ["Seasonal naive", "Exponential smoothing", "Gradient boosting"]
    for split in range(24, len(y)):
        for name in candidates:
            forecast = float(predict(y[:split], name)[0])
            backtests.append(
                {
                    "model": name,
                    "month": str(frame.month.iloc[split]),
                    "actual": float(y[split]),
                    "forecast": forecast,
                    "error": forecast - float(y[split]),
                }
            )
    scores = {
        name: float(np.mean([abs(r["error"]) for r in backtests if r["model"] == name]))
        for name in candidates
    }
    winner = min(scores, key=scores.get)
    errors = np.array([r["error"] for r in backtests if r["model"] == winner])
    radius = float(np.quantile(np.abs(errors), 0.9))
    future = predict(y, winner, 3)
    last = pd.Timestamp(frame.month.iloc[-1])
    metrics = {
        "mae": scores[winner],
        "wape": float(np.abs(errors).sum() / y[-len(errors) :].sum() * 100),
        "bias": float(errors.mean()),
        "interval_coverage": float(np.mean(np.abs(errors) <= radius) * 100),
    }
    report = {
        "kind": "forecast",
        "name": winner,
        "basis": "Invoiced revenue / GBP",
        "training_months": len(y),
        "backtest_origins": len(errors),
        "metrics": metrics,
        "candidate_mae": scores,
        "interval": "Empirical 90th-percentile absolute one-step backtest error; multi-step coverage is not established.",
        "scope": "Synthetic demonstration data; invoiced revenue is not bookings or recognised revenue.",
    }
    with session() as conn:
        version = store(conn, "ml.model_version", report, "registered")
        store(
            conn,
            "ml.evaluation_run",
            {"model_id": str(version["id"]), "backtests": backtests, **report},
            "passed",
        )
        conn.execute(
            text("DELETE FROM ml.prediction WHERE payload->>'kind'='forecast'")
        )
        for i, value in enumerate(future):
            store(
                conn,
                "ml.prediction",
                {
                    "kind": "forecast",
                    "month": str((last + pd.DateOffset(months=i + 1)).date()),
                    "value": round(max(0, float(value)), 2),
                    "lower": round(max(0, float(value) - radius), 2),
                    "upper": round(float(value) + radius, 2),
                    "model_id": str(version["id"]),
                },
                "scored",
            )
        # Seasonal deviations are measured, not narrated as business causes.
        residual = y[12:] - y[:-12]
        median = float(np.median(residual))
        mad = float(np.median(np.abs(residual - median)))
        cutoff = 3 * 1.4826 * mad
        anomalies = [
            {
                "month": str(frame.month.iloc[i + 12]),
                "value": float(y[i + 12]),
                "seasonal_delta": float(v),
                "flagged": bool(abs(v - median) > cutoff),
            }
            for i, v in enumerate(residual)
        ]
        store(
            conn,
            "ml.model_version",
            {
                "kind": "anomaly",
                "name": "Seasonal difference / robust MAD",
                "threshold": cutoff,
                "months": len(residual),
                "scope": "Retrospective synthetic-data screening; not a causal explanation.",
                "anomalies": anomalies,
            },
            "registered",
        )
    print("forecast", winner, json.dumps(metrics))


def main():
    with session() as conn:
        deals = rows(
            conn,
            """SELECT o.id,o.created_at+interval '30 days' snapshot_at,a.segment,a.region,o.lead_source,o.amount::float amount,
          (SELECT count(*)::float FROM core.activity x WHERE x.opportunity_id=o.id AND x.org_id=o.org_id AND x.occurred_at<=o.created_at+interval '30 days') activities,
          CASE WHEN o.stage='Won' AND o.closed_at<=o.created_at+interval '120 days' THEN 1 ELSE 0 END target
          FROM core.opportunity o JOIN core.account a ON (a.org_id,a.id)=(o.org_id,o.account_id)
          WHERE o.created_at+interval '120 days'<now() AND (o.closed_at IS NULL OR o.closed_at>o.created_at+interval '30 days')""",
        )
        churn = rows(
            conn,
            """SELECT s.id,s.started_at+interval '90 days' snapshot_at,a.segment,a.region,s.monthly_amount::float monthly_amount,
          (SELECT count(*)::float FROM finance.payment p JOIN finance.invoice i ON (p.org_id,p.invoice_id)=(i.org_id,i.id) WHERE i.account_id=s.account_id AND i.org_id=s.org_id AND p.paid_at<=s.started_at+interval '90 days') payments,
          CASE WHEN s.ended_at>s.started_at+interval '90 days' AND s.ended_at<=s.started_at+interval '180 days' THEN 1 ELSE 0 END target
          FROM finance.subscription s JOIN core.account a ON (a.org_id,a.id)=(s.org_id,s.account_id)
          WHERE s.started_at+interval '180 days'<now() AND (s.ended_at IS NULL OR s.ended_at>s.started_at+interval '90 days')""",
        )
    classification(
        "deal_win",
        deals,
        ["segment", "region", "lead_source", "amount", "activities"],
        ["segment", "region", "lead_source"],
    )
    classification(
        "churn",
        churn,
        ["segment", "region", "monthly_amount", "payments"],
        ["segment", "region"],
    )
    forecasts()


if __name__ == "__main__":
    main()
