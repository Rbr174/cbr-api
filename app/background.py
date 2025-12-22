# # currency_backend/background.py

import asyncio
from datetime import datetime
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import CurrencyRate
from app.services.cbr_service import fetch_rates, fetch_one_rate
from app.nats import publish


async def background_worker(interval: int = 120):
    while True:
        try:
            async with AsyncSessionLocal() as session:
                # Получаем все текущие курсы валют с сайта ЦБ
                rates = await fetch_rates()
                print(f"[Фоновая задача] Получено {len(rates)} валют")
                # Обрабатываем каждую валюту
                for r in rates:
                    # Получаем последний сохраненный курс для данной валюты
                    result = await session.execute(
                        select(CurrencyRate)
                        .where(CurrencyRate.code == r["code"])
                        .order_by(CurrencyRate.date.desc())
                        .limit(1)
                    )
                    last_rate = result.scalar_one_or_none()
                    # Проверка :если курс не изменился — пропускаем
                    if last_rate and last_rate.value == r["value"]:
                        continue

                    currency = CurrencyRate(
                        code=r["code"],
                        name=r["name"],
                        value=r["value"],
                        date=datetime.utcnow()
                    )
                    # Добавляем и сохраняем новую запись в БД
                    session.add(currency)
                    await session.commit()
                    await session.refresh(currency)

                    event = {
                        "event": "rate_updated" if last_rate else "rate_created",
                        "item": {
                            "id": currency.id,
                            "code": currency.code,
                            "name": currency.name,
                            "value": currency.value,
                            "date": currency.date.isoformat()
                        }
                    }

                    await publish("rates.updates", event)

                    print(
                        f"[Фоновая задача] {currency.code} = {currency.value} (id={currency.id})"
                    )

        except Exception as e:
            print(f"[Фоновая задача] Ошибка: {e}")

        await asyncio.sleep(interval)


async def run_manual_all():
    """
    Однократное получение всех курсов валют,
    проверка изменений и запись в базу при необходимости.
    Если курс не изменился — выводится сообщение "курс не обновился".
    """
    try:
        async with AsyncSessionLocal() as session:
            rates = await fetch_rates()  # Получаем все курсы
            if not rates:
                print("[Ручной запуск] Не удалось получить валюты")
                return

            for r in rates:
                # Получаем последний сохраненный курс для этой валюты
                result = await session.execute(
                    select(CurrencyRate)
                    .where(CurrencyRate.code == r["code"])
                    .order_by(CurrencyRate.date.desc())
                    .limit(1)
                )
                last_rate = result.scalar_one_or_none()

                if last_rate:
                    if last_rate.value == r["value"]:
                        # Курс не изменился
                        print(
                            f"[Ручной запуск] {r['code']}: курс не обновился (остался {r['value']})")
                        continue
                    else:
                        msg = f"[Ручной запуск] {r['code']} изменился с {last_rate.value} на {r['value']}"
                else:
                    msg = f"[Ручной запуск] {r['code']} добавлен в базу со значением {r['value']}"

                # Создаем новую запись
                currency = CurrencyRate(
                    code=r["code"],
                    name=r["name"],
                    value=r["value"],
                    date=datetime.utcnow()
                )

                # Сохраняем в базу
                session.add(currency)
                await session.commit()
                await session.refresh(currency)

                # Выводим сообщение о создании или изменении курса
                print(f"{msg} (id={currency.id})")

    except Exception as e:
        print(f"[Ручной запуск] Ошибка: {e}")
