WITH aggregate AS (
 SELECT org_id,month,sum(invoiced_revenue) invoiced_revenue FROM {{ref('monthly_revenue')}} GROUP BY org_id,month
), lagged AS (
 SELECT *,lag(invoiced_revenue) OVER(PARTITION BY org_id ORDER BY month) prior_month,
 lag(invoiced_revenue,12) OVER(PARTITION BY org_id ORDER BY month) prior_year,
 sum(invoiced_revenue) OVER(PARTITION BY org_id ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) rolling_three_months
 FROM aggregate
)
SELECT *,100*(invoiced_revenue-prior_month)/nullif(prior_month,0) month_growth_percent,
100*(invoiced_revenue-prior_year)/nullif(prior_year,0) year_growth_percent FROM lagged
