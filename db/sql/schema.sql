CREATE SCHEMA identity;
CREATE SCHEMA integration;
CREATE SCHEMA raw;
CREATE SCHEMA core;
CREATE SCHEMA finance;
CREATE SCHEMA planning;
CREATE SCHEMA mart;
CREATE SCHEMA ml;
CREATE SCHEMA ai;
CREATE SCHEMA automation;
CREATE SCHEMA ops;
CREATE SCHEMA reporting;

CREATE TABLE identity.organisation(id uuid PRIMARY KEY, name text NOT NULL, demo boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE core.sales_rep(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, name text NOT NULL, region text NOT NULL, UNIQUE(org_id,id));
CREATE TABLE core.account(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, name text NOT NULL, segment text NOT NULL CHECK(segment IN ('Enterprise','Mid-market','SMB')), region text NOT NULL, owner_id uuid NOT NULL, acquired_at timestamptz NOT NULL, UNIQUE(org_id,id), FOREIGN KEY(org_id,owner_id) REFERENCES core.sales_rep(org_id,id));
CREATE TABLE core.contact(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, account_id uuid NOT NULL, name text NOT NULL, email text, UNIQUE(org_id,id), FOREIGN KEY(org_id,account_id) REFERENCES core.account(org_id,id));
CREATE TABLE core.opportunity(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, account_id uuid NOT NULL, owner_id uuid NOT NULL, name text NOT NULL, stage text NOT NULL CHECK(stage IN ('Discovery','Qualified','Proposal','Negotiation','Won','Lost')), amount numeric(18,2) NOT NULL CHECK(amount>=0), currency char(3) NOT NULL DEFAULT 'GBP', created_at timestamptz NOT NULL, expected_close timestamptz NOT NULL, closed_at timestamptz, stage_entered_at timestamptz NOT NULL, lead_source text NOT NULL, lost_reason text, UNIQUE(org_id,id), FOREIGN KEY(org_id,account_id) REFERENCES core.account(org_id,id), FOREIGN KEY(org_id,owner_id) REFERENCES core.sales_rep(org_id,id));
CREATE TABLE core.opportunity_stage_history(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, opportunity_id uuid NOT NULL, from_stage text, to_stage text NOT NULL, occurred_at timestamptz NOT NULL, FOREIGN KEY(org_id,opportunity_id) REFERENCES core.opportunity(org_id,id));
CREATE TABLE core.activity(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, opportunity_id uuid NOT NULL, kind text NOT NULL, occurred_at timestamptz NOT NULL, FOREIGN KEY(org_id,opportunity_id) REFERENCES core.opportunity(org_id,id));
CREATE TABLE finance.subscription(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, account_id uuid NOT NULL, monthly_amount numeric(18,2) NOT NULL CHECK(monthly_amount>=0), currency char(3) NOT NULL DEFAULT 'GBP', started_at timestamptz NOT NULL, ended_at timestamptz, UNIQUE(org_id,id), FOREIGN KEY(org_id,account_id) REFERENCES core.account(org_id,id), CHECK(ended_at IS NULL OR ended_at>=started_at));
CREATE TABLE finance.invoice(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, account_id uuid NOT NULL, subscription_id uuid, amount numeric(18,2) NOT NULL CHECK(amount>=0), currency char(3) NOT NULL DEFAULT 'GBP', issued_at timestamptz NOT NULL, due_at timestamptz NOT NULL, UNIQUE(org_id,id), FOREIGN KEY(org_id,account_id) REFERENCES core.account(org_id,id), FOREIGN KEY(org_id,subscription_id) REFERENCES finance.subscription(org_id,id));
CREATE TABLE finance.invoice_line(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, invoice_id uuid NOT NULL, description text NOT NULL, amount numeric(18,2) NOT NULL, FOREIGN KEY(org_id,invoice_id) REFERENCES finance.invoice(org_id,id));
CREATE TABLE finance.payment(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, invoice_id uuid NOT NULL, amount numeric(18,2) NOT NULL CHECK(amount>0), paid_at timestamptz NOT NULL, FOREIGN KEY(org_id,invoice_id) REFERENCES finance.invoice(org_id,id));
CREATE TABLE finance.credit_note(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, invoice_id uuid NOT NULL, amount numeric(18,2) NOT NULL CHECK(amount>0), issued_at timestamptz NOT NULL, FOREIGN KEY(org_id,invoice_id) REFERENCES finance.invoice(org_id,id));
CREATE TABLE finance.revenue_entry(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, invoice_id uuid NOT NULL, amount numeric(18,2) NOT NULL, recognised_at timestamptz NOT NULL, accounting_source text NOT NULL, FOREIGN KEY(org_id,invoice_id) REFERENCES finance.invoice(org_id,id));
CREATE TABLE planning.revenue_target(id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES identity.organisation, month date NOT NULL, amount numeric(18,2) NOT NULL CHECK(amount>=0), currency char(3) NOT NULL DEFAULT 'GBP', UNIQUE(org_id,month));

-- Operational documents have typed identity, tenancy, state and immutable provenance.
DO $$ DECLARE item text; schema_name text; table_name text; BEGIN
 FOREACH item IN ARRAY ARRAY['identity.user','identity.membership','identity.role','integration.connection','integration.sync_run','integration.cursor','integration.webhook_event','raw.source_record','raw.import_batch','raw.import_error','finance.subscription_event','planning.quota','planning.forecast_scenario','ml.feature_snapshot','ml.model_version','ml.prediction','ml.evaluation_run','ai.conversation','ai.message','ai.tool_execution','ai.evidence_reference','automation.rule','automation.execution','automation.approval','automation.action','automation.audit_event','ops.quality_result','ops.job_run','ops.data_freshness','reporting.report','reporting.saved_view','reporting.schedule'] LOOP
  schema_name := split_part(item,'.',1); table_name := split_part(item,'.',2);
  EXECUTE format('CREATE TABLE %I.%I(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid NOT NULL REFERENCES identity.organisation, status text NOT NULL, payload jsonb NOT NULL DEFAULT ''{}'', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), version integer NOT NULL DEFAULT 1 CHECK(version>0), idempotency_key text, UNIQUE(org_id,id), UNIQUE(org_id,idempotency_key))',schema_name,table_name);
 END LOOP;
END $$;

CREATE INDEX opportunity_period ON core.opportunity(org_id,created_at);
CREATE INDEX opportunity_account ON core.opportunity(org_id,account_id);
CREATE INDEX opportunity_stage ON core.opportunity(org_id,stage,stage_entered_at);
CREATE INDEX invoice_period ON finance.invoice(org_id,issued_at);
CREATE INDEX invoice_account ON finance.invoice(org_id,account_id);
CREATE INDEX activity_opportunity ON core.activity(org_id,opportunity_id,occurred_at);
CREATE INDEX stage_opportunity ON core.opportunity_stage_history(org_id,opportunity_id,occurred_at);
CREATE INDEX subscription_account ON finance.subscription(org_id,account_id,started_at);

DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT table_schema,table_name FROM information_schema.columns WHERE column_name='org_id' AND table_schema IN ('identity','integration','raw','core','finance','planning','ml','ai','automation','ops','reporting') LOOP
  EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',t.table_schema,t.table_name);
  EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY',t.table_schema,t.table_name);
  EXECUTE format('CREATE POLICY tenant_scope ON %I.%I USING (org_id = nullif(current_setting(''app.org_id'',true),'''')::uuid) WITH CHECK (org_id = nullif(current_setting(''app.org_id'',true),'''')::uuid)',t.table_schema,t.table_name);
  EXECUTE format('CREATE INDEX ON %I.%I(org_id)',t.table_schema,t.table_name);
 END LOOP;
END $$;
ALTER TABLE identity.organisation ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.organisation FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_org ON identity.organisation USING(id=nullif(current_setting('app.org_id',true),'')::uuid);

CREATE VIEW mart.monthly_revenue WITH (security_invoker=true) AS
 SELECT i.org_id,date_trunc('month',i.issued_at)::date AS month,a.segment,a.region,sum(i.amount) AS invoiced_revenue,count(*) AS invoices
 FROM finance.invoice i JOIN core.account a ON (a.org_id,a.id)=(i.org_id,i.account_id)
 GROUP BY i.org_id,date_trunc('month',i.issued_at)::date,a.segment,a.region;
CREATE VIEW mart.pipeline WITH (security_invoker=true) AS
 SELECT o.*,a.name AS account,a.segment,a.region,r.name AS owner,
 CASE o.stage WHEN 'Discovery' THEN .15 WHEN 'Qualified' THEN .35 WHEN 'Proposal' THEN .55 WHEN 'Negotiation' THEN .75 WHEN 'Won' THEN 1 ELSE 0 END AS stage_weight,
 extract(day from now()-o.stage_entered_at)::integer AS days_in_stage
 FROM core.opportunity o JOIN core.account a ON (a.org_id,a.id)=(o.org_id,o.account_id) JOIN core.sales_rep r ON (r.org_id,r.id)=(o.org_id,o.owner_id);
CREATE VIEW mart.invoice_balance WITH (security_invoker=true) AS
 SELECT i.*,i.amount-coalesce((SELECT sum(p.amount) FROM finance.payment p WHERE p.org_id=i.org_id AND p.invoice_id=i.id),0)-coalesce((SELECT sum(c.amount) FROM finance.credit_note c WHERE c.org_id=i.org_id AND c.invoice_id=i.id),0) AS outstanding
 FROM finance.invoice i;

GRANT USAGE ON SCHEMA identity,integration,raw,core,finance,planning,mart,ml,ai,automation,ops,reporting TO revpilot_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA identity,integration,raw,core,finance,planning,ml,ai,automation,ops,reporting TO revpilot_app;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO revpilot_app;
