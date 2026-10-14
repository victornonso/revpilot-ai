# Automation specification

Implemented local path: saved rule → bounded simulation/evaluation → exact action
proposal → pending approval → approved/rejected → Temporal workflow → recorded
internal demonstration task. No customer email or CRM mutation is performed.

Rules currently support an executable AND/OR combination of stage age and
opportunity amount, with a cooldown. The worker dispatches persisted pending
actions to stable Temporal workflow IDs. Each workflow polls a persisted approval
with durable timers. Execution checks the canonical action hash and approval
again, locks the action row and uses a database idempotency key.

Approval decisions require the version reviewed by the caller. Editing an action
invalidates its hash. Replay is rejected. Expiry is enforced. Actual execution
and audit records are stored transactionally. Native Temporal development-server
history is persisted locally; it is not production hosting.

Eight template concepts are present in the UI. Their distinct entity/trigger/
condition adapters are not all implemented; the executable builder currently
uses opportunity age/value conditions. Production multi-tenant dispatch,
payload-edit/resubmission, durable schedules, cancellation, external adapters,
capacity controls and outcome tracking remain acceptance work.
