# currency_backend/websocket.py

from fastapi import WebSocket
from app.database import AsyncSessionLocal
from app.models import CurrencyRate
from sqlalchemy import select


class WSManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(
            f"[WebSocket] Клиент подключён: {websocket.client}, всего клиентов: {len(self.active_connections)}")

        # При подключении отправляем текущие курсы валют
        await self.send_current_rates(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(
                f"[WebSocket] Клиент отключён: {websocket.client}, осталось клиентов: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(
                    f"[WebSocket] Ошибка отправки сообщения клиенту {ws.client}: {e}")
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)
        print(
            f"[WebSocket] Сообщение отправлено {len(self.active_connections)} клиентам: {message}")

    async def send_current_rates(self, websocket: WebSocket):
        """Отправка текущих курсов валют при подключении нового клиента"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(CurrencyRate))
            rates = result.scalars().all()
            data = {
                "event": "current_rates",
                "items": [
                    {
                        "id": r.id,
                        "code": r.code,
                        "name": r.name,
                        "value": r.value,
                        "date": r.date.isoformat()
                    } for r in rates
                ]
            }
            await websocket.send_json(data)
            print(
                f"[WebSocket] Отправлен текущий список курсов клиенту {websocket.client}, всего {len(rates)} валют")


manager = WSManager()
