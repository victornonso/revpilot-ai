# Model methodology

All measured results are **synthetic demonstration performance**. They do not
establish performance on real sales or customer populations.

Deal classification uses features available 30 days after creation. Records
closed before that snapshot are excluded. The target is a win within the
following 90 days. Activity counts stop at the snapshot; account segment, region,
lead source and amount are included. Churn classification uses subscription
snapshots 90 days after start, payment counts restricted to that time, segment,
region and monthly value; the target is cancellation in the following 90 days.

For each classifier, train before 2025, select Logistic Regression or LightGBM
using 2025 validation Brier score, refit the development partition and evaluate
2026 observations. Fitted preprocessing belongs inside the pipeline. The saved
reports include PR-AUC, ROC-AUC, Brier score and empirical calibration bins.

Revenue forecasting compares seasonal naive, additive seasonal exponential
smoothing and lagged gradient boosting. Rolling one-step origins start after
24 months; the lowest backtest MAE selects the family. The final three-month
forecast is invoiced revenue, not bookings or recurring revenue. Empirical
absolute-error intervals describe observed one-step backtest errors; joint or
multi-step coverage is not established.

Anomaly screening uses seasonal differences and a robust median/MAD threshold.
It is retrospective screening, not attribution of business causes. Feature/model
artefacts remain local and are tracked in MLflow with their measured reports.

Remaining work includes separate bookings/recurring forecasts, live batch scoring,
lift/capacity evaluation, drift/rollback operations and complete feature snapshot
storage. Models currently display historical held-out predictions; stage weights
are explicitly labelled heuristics rather than model win probabilities.
