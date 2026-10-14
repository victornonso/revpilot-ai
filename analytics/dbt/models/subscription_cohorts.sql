WITH cohorts AS (
 SELECT org_id,date_trunc('month',started_at)::date cohort,generate_series(0,11) months_since_start,
 account_id,started_at,ended_at
 FROM finance.subscription
), observed AS (
 SELECT *,cohort+make_interval(months=>months_since_start+1) period_end
 FROM cohorts
)
SELECT org_id,cohort,months_since_start,count(DISTINCT account_id) starting_accounts,
count(DISTINCT account_id) FILTER(WHERE ended_at IS NULL OR ended_at>=period_end) retained_accounts,
100.0*count(DISTINCT account_id) FILTER(WHERE ended_at IS NULL OR ended_at>=period_end)/nullif(count(DISTINCT account_id),0) retention_percent
FROM observed WHERE period_end<=now() AND started_at<cohort+interval '1 month'
GROUP BY org_id,cohort,months_since_start
