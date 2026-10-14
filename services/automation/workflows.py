from datetime import timedelta

from temporalio import workflow


@workflow.defn
class FollowUpWorkflow:
    @workflow.run
    async def run(self, action_id: str) -> dict:
        for _ in range(5760):
            state = await workflow.execute_activity(
                "approval_state",
                action_id,
                start_to_close_timeout=timedelta(seconds=20),
            )
            if state in ("rejected", "expired", "cancelled"):
                return {"status": state}
            if state == "approved":
                return await workflow.execute_activity(
                    "execute_demo_action",
                    action_id,
                    start_to_close_timeout=timedelta(seconds=30),
                )
            await workflow.sleep(timedelta(seconds=30))
        return {"status": "expired"}
