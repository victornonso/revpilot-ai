SELECT o.org_id,o.owner_id,r.name,
 count(*) FILTER(WHERE stage='Won') won,
 count(*) FILTER(WHERE stage='Lost') lost,
 sum(amount) FILTER(WHERE stage='Won') bookings,
 percentile_cont(.5) WITHIN GROUP(ORDER BY extract(epoch FROM closed_at-created_at)/86400) FILTER(WHERE stage='Won') median_cycle_days,
 dense_rank() OVER(PARTITION BY o.org_id ORDER BY sum(amount) FILTER(WHERE stage='Won') DESC NULLS LAST) revenue_rank,
 ntile(4) OVER(PARTITION BY o.org_id ORDER BY sum(amount) FILTER(WHERE stage='Won') DESC NULLS LAST) quartile
FROM core.opportunity o JOIN core.sales_rep r ON (o.org_id,o.owner_id)=(r.org_id,r.id)
GROUP BY o.org_id,o.owner_id,r.name
