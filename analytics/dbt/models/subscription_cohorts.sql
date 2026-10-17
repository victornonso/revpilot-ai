WITH cohorts AS (
 SELECT s.org_id,a.segment,date_trunc('month',s.started_at)::date cohort,generate_series(0,11) months_since_start,
 s.account_id,s.started_at,s.ended_at
 FROM finance.subscription s JOIN core.account a ON (a.org_id,a.id)=(s.org_id,s.account_id)
), observed AS (
 SELECT *,cohort+make_interval(months=>months_since_start+1) period_end
 FROM cohorts
)
SELECT org_id,segment,cohort,months_since_start,count(DISTINCT account_id) starting_accounts,
count(DISTINCT account_id) FILTER(WHERE ended_at IS NULL OR ended_at>=period_end) retained_accounts,
100.0*count(DISTINCT account_id) FILTER(WHERE ended_at IS NULL OR ended_at>=period_end)/nullif(count(DISTINCT account_id),0) retention_percent
FROM observed WHERE period_end<=now() AND started_at<cohort+interval '1 month'
GROUP BY org_id,segment,cohort,months_since_start
