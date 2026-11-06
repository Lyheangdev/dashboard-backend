from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.lib.api_enum import ApiTagEnum
from src.config.line import SocialLine

router = APIRouter(prefix="/admin/third-party", tags=[ApiTagEnum.THIRD_PARTY])


class LinnPushPayload(BaseModel):
    user_id: str
    message: str | None = None


# Line bot push notification test
@router.post("/line/notification/push")
async def pushNotification(payload: LinnPushPayload, socialLine: SocialLine):
    messageDefault = """
🏭 SMART PRODUCTION DASHBOARD

Good morning!

Welcome to the Smart Production Dashboard.

📊 PRODUCTION OVERVIEW
━━━━━━━━━━━━━━━━━━
• Monitor production performance and output.
• Track production targets versus actual results.
• Analyze production efficiency and productivity.

⚡ REAL-TIME INSIGHTS
━━━━━━━━━━━━━━━━━━
Stay informed with up-to-date production information.

🎯 OUR GOAL
━━━━━━━━━━━━━━━━━━
Transform production data into actionable insights.
"""

    response_msg = payload.message or messageDefault
    await socialLine.pushMessage(payload.user_id, message=response_msg)
    return {"status": "push success"}


@router.post("/line/webhook")
async def lineWebhook(request: Request):
    try:
        payload = await request.json()
        print(payload)

        for event in payload.get("events", []):
            event_type = event.get("type")

            if event_type == "message":
                user_id = event.get("source", {}).get("userId")

                if user_id:
                    print(f"LINE User ID: {user_id}")

            # if bot join the group
            if event_type == "join":
                group_id = event.get("source", {}).get("groupId")

                if group_id:
                    print(f"Bot leaved the LINE group ID: {group_id}")

            if event_type == "leave":
                group_id = event.get("source", {}).get("groupId")

                if group_id:
                    print(f"Bot leaved the LINE group ID: {group_id}")

        return {"status": "success"}

    except Exception as e:
        print(f"LINE webhook error: {e}")
        return {"status": "error"}
