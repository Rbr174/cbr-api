# currency_backend/schemas.py

from pydantic import BaseModel
from datetime import datetime


class RateBase(BaseModel):
    code: str
    name: str
    value: float


class RateOut(RateBase):
    id: int
    date: datetime

    model_config = {
        "from_attributes": True
    }
