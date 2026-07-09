import json

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken


class ExpertRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self._read_token()
        if not token:
            await self.close(code=4001)
            return
        try:
            payload = AccessToken(token)
            is_admin = bool(payload.get("is_admin"))
            if not is_admin:
                await self.close(code=4003)
                return
        except Exception:
            await self.close(code=4002)
            return

        self.group_name = "admin_expert_requests"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Keepalive only; server pushes notifications from API create().
        return

    async def expert_request_created(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "event": event.get("event", "expert_request_created"),
                    "request": event.get("request"),
                    "summary": event.get("summary"),
                }
            )
        )

    def _read_token(self) -> str:
        query_string = self.scope.get("query_string", b"").decode()
        parts = [p for p in query_string.split("&") if p.startswith("token=")]
        if parts:
            return parts[0].split("=", 1)[1]
        for name, value in self.scope.get("headers", []):
            if name == b"authorization":
                raw = value.decode()
                if raw.lower().startswith("bearer "):
                    return raw[7:].strip()
        return ""
