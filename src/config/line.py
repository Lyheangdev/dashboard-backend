from typing import Annotated, Literal, Protocol

import httpx as httpClient
from fastapi import BackgroundTasks, Depends

from src.lib.utils import getCurrentTime


class LineService:
    CHANNEL_ACCESS_TOKEN = (
        "kYJ6SBMn4nPTcfyc6gZS9hEJAdN4zUPgvwcYs0JzkC6fsnV7LajnJrj"
        "48zFKLClYkYsJG5h5+DcW/d8ME8liWdQzL+bJLiZ8Jt6rPEn7oMVOMhIO4EVRsKYe/K40HZBYyNNzI7bAdOTNpZ5a7fFr7QdB04t89/1O/w1cDnyilFU="
    )
    BaseUrl = "https://api.line.me/v2/bot/message/push"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    async def pushMessage(self, user_id: str, message: str):
        payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
        async with httpClient.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.BaseUrl, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json() if response.content else {}


def socialLineDeps():
    lineService = LineService()
    return lineService


SocialLine = Annotated[LineService, Depends(socialLineDeps)]


def lineMessageTemplate(
    *,
    email: str,
    host: str | None,
    mode: str,
    action: str | None,
    status: Literal["SUCCESS", "FAILED", "PENDING"],
):
    status_label = (status or "").upper()

    status_icon = {
        "SUCCESS": "✅",
        "FAILED": "❌",
        "PENDING": "⏳",
    }.get(status_label, "⚠️")

    markdown = f"""
📋 SYSTEM LOGIC HISTORY
━━━━━━━━━━━━━━━━━━━━

👤 User        : {email}
🌐 IP Address  : {host or "Unknown"}
⚙️ Environment : {mode}
🔧 Action      : {action or "N/A"}
🕒 Timestamp   : {getCurrentTime()}

{status_icon} Status      : {status_label}
━━━━━━━━━━━━━━━━━━━━
""".strip()

    return markdown


class SocialLineTaskRunnerType(Protocol):
    def __call__(
        self,
        *,
        email: str,
        host: str | None,
        mode: str,
        action: str | None,
        status: Literal["SUCCESS", "FAILED", "PENDING"] = "SUCCESS",
    ) -> None: ...


def excuteProcessToSendLineMessage(
    socialLine: SocialLine, background: BackgroundTasks
) -> SocialLineTaskRunnerType:
    def excuteLineMessageTaskRunner(
        *,
        email: str,
        host: str | None,
        mode: str,
        action: str | None,
        status: Literal["SUCCESS", "FAILED", "PENDING"],
    ) -> None:
        markdown_result_msg = lineMessageTemplate(
            email=email, host=host, mode=mode, action=action, status=status
        )

        background.add_task(
            socialLine.pushMessage,
            user_id="C4981bf0b68ee3b05902cfa33fb4dca8a",
            message=markdown_result_msg,
        )

    return excuteLineMessageTaskRunner


SocialLineTaskRunner = Annotated[
    SocialLineTaskRunnerType,
    Depends(excuteProcessToSendLineMessage),
]
