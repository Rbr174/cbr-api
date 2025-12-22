# # ##currency_backend/api/tasks.py

from fastapi import APIRouter
import asyncio
from app.background import run_manual_all

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/run")
async def run_task():
    """
    Ручной запуск парсинга всех курсов валют.
    Асинхронно запускает функцию run_manual_all в фоне.
    """
    asyncio.create_task(run_manual_all())  # Запускаем асинхронно в фоне
    return {
        "status": "started",
        "message": "Ручной запуск парсинга запущен"
    }
