# #currency_backend/api/rates.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import CurrencyRate
from app.schemas import RateBase, RateOut
from app.nats import publish

router = APIRouter(prefix="/rates", tags=["rates"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=list[RateOut])
async def list_rates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CurrencyRate))
    return result.scalars().all()


@router.get("/{rate_id}", response_model=RateOut)
async def get_rate(rate_id: int, db: AsyncSession = Depends(get_db)):
    rate = await db.get(CurrencyRate, rate_id)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    return rate


@router.post("", response_model=RateOut)
async def create_rate(data: RateBase, db: AsyncSession = Depends(get_db)):
    rate = CurrencyRate(**data.dict())
    db.add(rate)
    await db.commit()
    await db.refresh(rate)

    # Публикуем событие в NATS
    await publish("rates.updates", {
        "event": "create",
        "item": {
            "id": rate.id,
            "code": rate.code,
            "name": rate.name,
            "value": rate.value,
            "date": rate.date.isoformat()
        }
    })

    return rate


@router.patch("/{rate_id}", response_model=RateOut)
async def update_rate(rate_id: int, data: RateBase, db: AsyncSession = Depends(get_db)):
    rate = await db.get(CurrencyRate, rate_id)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(rate, field, value)
    await db.commit()
    await db.refresh(rate)

    # Публикуем событие
    await publish("rates.updates", {
        "event": "update",
        "item": {
            "id": rate.id,
            "code": rate.code,
            "name": rate.name,
            "value": rate.value,
            "date": rate.date.isoformat()
        }
    })

    return rate


@router.delete("/{rate_id}", status_code=204)
async def delete_rate(rate_id: int, db: AsyncSession = Depends(get_db)):
    rate = await db.get(CurrencyRate, rate_id)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    # Сохраняем данные для уведомления перед удалением
    data_to_send = {
        "id": rate.id,
        "code": rate.code,
        "name": rate.name,
        "value": rate.value,
        "date": rate.date.isoformat()
    }

    await db.delete(rate)
    await db.commit()

    # Публикуем событие
    await publish("rates.updates", {
        "event": "delete",
        "item": data_to_send
    })
