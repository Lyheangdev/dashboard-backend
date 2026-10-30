import httpx as httpClient


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


lineService = LineService()
