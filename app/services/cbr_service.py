# currency_backend/cbr-service.py

import httpx
from xml.etree import ElementTree
import random

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


async def fetch_rates(limit: int | None = None):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(CBR_URL)
        response.raise_for_status()

    tree = ElementTree.fromstring(response.text)
    rates = []

    for v in tree.findall("Valute"):
        rates.append({
            "code": v.findtext("CharCode"),
            "name": v.findtext("Name"),
            "value": float(v.findtext("Value").replace(",", "."))
        })

        if limit and len(rates) >= limit:
            break

    return rates


async def fetch_one_rate():
    rates = await fetch_rates()
    return random.choice(rates) if rates else None




