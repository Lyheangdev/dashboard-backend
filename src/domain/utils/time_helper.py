from datetime import datetime
from zoneinfo import ZoneInfo


def getCurrentTime() -> str:
    now = datetime.now(ZoneInfo("Asia/Phnom_Penh"))
    return now.strftime("%Y-%m-%d %H:%M:%S")
