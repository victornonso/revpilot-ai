import json

import mlflow
from sqlalchemy import text

from apps.api.db import ROOT, rows, session

mlflow.set_tracking_uri(
    "sqlite:///" + str(ROOT / ".local/mlflow.db").replace("\\", "/")
)
mlflow.set_experiment("RevPilot / synthetic benchmarks")
with session() as conn:
    versions = rows(conn, "SELECT id,payload FROM ml.model_version ORDER BY created_at")
for version in versions:
    payload = version["payload"]
    with mlflow.start_run(run_name=payload["kind"] + " / " + payload["name"]) as run:
        mlflow.set_tags(
            {
                "data_mode": "synthetic",
                "organisation": "Northstar Cloud",
                "kind": payload["kind"],
            }
        )
        mlflow.log_params(
            {
                k: payload[k]
                for k in [
                    "train_rows",
                    "validation_rows",
                    "test_rows",
                    "training_months",
                    "backtest_origins",
                ]
                if k in payload
            }
        )
        mlflow.log_metrics(payload.get("metrics", {}))
        mlflow.log_dict(payload, "evaluation.json")
        artifact = ROOT / ".local/models" / (payload["kind"] + ".joblib")
        if artifact.exists():
            mlflow.log_artifact(str(artifact))
        with session() as conn:
            conn.execute(
                text(
                    "UPDATE ml.model_version SET payload=payload || cast(:extra as jsonb) WHERE id=:id"
                ),
                {
                    "extra": json.dumps({"mlflow_run_id": run.info.run_id}),
                    "id": version["id"],
                },
            )
print("Tracked measured evaluation reports and fitted model artefacts in local MLflow.")
