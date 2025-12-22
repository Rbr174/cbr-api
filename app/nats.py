# currency_backend/nats.py

import json
from nats.aio.client import Client as NATS
from app.websocket import manager

nc = NATS()


async def connect_nats():
    await nc.connect("nats://localhost:4222")
    print("[NATS] Подключено к серверу NATS")
    await nc.subscribe("rates.updates", cb=message_handler)
    print("[NATS] Подписка на канал rates.updates выполнена")


async def publish(subject: str, data: dict):
    if not nc.is_connected:
        await connect_nats()
    await nc.publish(subject, json.dumps(data).encode())
    print(f"[NATS] Опубликовано в {subject}: {data}")


async def message_handler(msg):
    data = json.loads(msg.data.decode())
    print(f"[NATS] Получено сообщение: {data}")
    # Отправляем всем подключённым WebSocket клиентам
    await manager.broadcast(data)
