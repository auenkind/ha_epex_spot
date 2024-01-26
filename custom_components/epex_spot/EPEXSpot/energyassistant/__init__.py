import logging
from datetime import datetime, timedelta, timezone

import aiohttp, json
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)


class Marketprice:
    UOM_EUR_PER_MWh = "EUR/MWh"
    UOM_CT_PER_kWh = "ct/kWh"

    def __init__(self, data):
        # assert data["unit"].lower() == self.UOM_EUR_PER_MWh.lower()
        self._start_time = datetime.fromisoformat(data["datetime"])
        self._end_time = self._start_time + timedelta(hours=1)
        self._price_ct_per_kwh = data["price"]

    def __repr__(self):
        return f"{self.__class__.__name__}(start: {self._start_time.isoformat()}, end: {self._end_time.isoformat()}, marketprice: {self._price_ct_per_kwh} {self.UOM_CT_PER_kWh})"  # noqa: E501

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def price_eur_per_mwh(self):
        return round(self._price_ct_per_kwh * 10, 2)

    @property
    def price_ct_per_kwh(self):
        return self._price_ct_per_kwh


def toEpochMilliSec(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class EnergyAssistant:
    URL = "https://{api_domain}/api/stockmarket/v1/mapped-values"
    LOGIN_URL = "https://{api_domain}/api/auth/v1/customer/login"

    MARKET_AREA_DOMAINS = {"Haßfurt": "hassfurt.energy-assistant.de"}

    MARKET_AREAS = list(MARKET_AREA_DOMAINS.keys())

    def __init__(
        self, market_area, username: str, password: str, session: aiohttp.ClientSession
    ):
        self._session = session
        self._market_area = market_area
        self._username = username
        self._password = password

        self._url = self.URL.format(
            api_domain=self.MARKET_AREA_DOMAINS[self._market_area]
        )
        self._login_url = self.LOGIN_URL.format(
            api_domain=self.MARKET_AREA_DOMAINS[self._market_area]
        )
        self._marketdata = []

    @property
    def name(self):
        return ""

    @property
    def market_area(self):
        return self._market_area

    @property
    def duration(self):
        return 60

    @property
    def currency(self):
        return "EUR"

    @property
    def marketdata(self):
        return self._marketdata

    async def fetch(self):
        tokenResp = await self._fetch_token()
        token = tokenResp["token"]
        data = await self._fetch_data(self._url, token)
        self._marketdata = self._extract_marketdata(data["values"])

    async def _fetch_token(self):
        bodyData = {"email": self._username, "password": self._password}

        async with self._session.post(self._login_url, json=bodyData) as resp:
            resp.raise_for_status()
            respData = resp.json()
            return await respData

    async def _fetch_data(self, url, token):
        today = datetime.now()
        start = datetime(today.year, today.month, today.day)
        end = start + timedelta(days=2)

        url = "{endpoint}/startdate/{startdate}Z/enddate/{enddate}Z/interval/{interval}".format(
            endpoint=url,
            startdate=start.isoformat(),
            enddate=end.isoformat(),
            interval="hour",
        )
        headers = {"Authorization": "Bearer {}".format(token)}

        async with self._session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _extract_marketdata(self, data):
        entries = []
        for entry in data:
            entries.append(Marketprice(entry))
        return entries
