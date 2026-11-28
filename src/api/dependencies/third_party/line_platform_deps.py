from typing import Annotated, Literal, Protocol

from fastapi import BackgroundTasks, Depends

from src.domain.utils.time_helper import getCurrentTime
from src.infrastructure.third_party.line_platform import LineService


# --- First deps
def socialLineDeps():
    lineService = LineService()
    return lineService


SocialLine = Annotated[LineService, Depends(socialLineDeps)]


# --- Second deps
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
