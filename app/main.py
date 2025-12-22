# # # #currency_backend/main.py
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio

from app.websocket import manager
from app.api import rates, tasks
from app.database import init_db
from app.background import background_worker
from app.nats import connect_nats

app = FastAPI(title="CBR Currency Rates")

app.include_router(rates.router)
app.include_router(tasks.router)

# Флаг, чтобы фоновая задача стартовала один раз
_background_task_started = False


@app.websocket("/ws/items")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.on_event("startup")
async def startup():
    global _background_task_started

    await init_db()
    print("[Приложение] База инициализирована")

    # Подключение к NATS
    asyncio.create_task(connect_nats())

    # Фоновая задача — ТОЛЬКО ОДИН РАЗ
    if not _background_task_started:
        asyncio.create_task(background_worker(interval=60))
        _background_task_started = True
        print("[Приложение] Фоновая задача авто-парсера запущена")
