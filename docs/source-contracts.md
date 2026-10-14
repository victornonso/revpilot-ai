# Source contracts

## Demonstration data

Seed 20261014, source anchor 14 October 2026, approximately 36 months of history.
Names and emails are synthetic; emails use the reserved example.test domain.
Re-running generation preserves an existing demo tenant rather than overwriting
interactive actions. Invoices reconcile to their lines. Payments reference valid
invoices and do not exceed their face amount in this generator.

## Account imports

CSV and .xlsx; at most 2 MB / 10,000 rows / 50 unique columns. Required mapped
fields are name, segment and region. Segments are Enterprise, Mid-market or SMB.
The entire confirmation is rejected if any row is invalid. Loaded rows and job
history share a single transaction. Additional entity loaders are not implemented.

## External clients

HubSpot: documented CRM v3 object reads, cursor pagination, property metadata,
pipelines and owner reads. Stripe: customer/subscription/invoice/payment/refund/
credit-note pagination, plus invoice-line reads. Bounded retry handles 429 and 5xx.
Stripe webhook verification checks HMAC over the original raw body and time skew.

These HTTP clients have mocked-contract tests. They are not connected live.
Full incremental canonicalisation, custom property mapping, associations,
deletion reconciliation, encrypted credential management and webhook endpoint
ingestion remain unfinished. A tested client is not a completed production sync.

Official contracts checked 14 October 2026:
- https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/deals/guide
- https://docs.stripe.com/webhooks
- https://docs.temporal.io/develop/python
- https://www.postgresql.org/docs/18/ddl-rowsecurity.html
