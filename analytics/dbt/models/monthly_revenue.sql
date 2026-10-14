SELECT i.org_id, date_trunc('month',i.issued_at)::date AS month,
       a.segment, a.region, sum(i.amount) AS invoiced_revenue, count(*) AS invoices
FROM finance.invoice i
JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id)
GROUP BY i.org_id,date_trunc('month',i.issued_at)::date,a.segment,a.region
