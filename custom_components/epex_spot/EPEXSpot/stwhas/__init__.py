from datetime import datetime, timedelta
import logging

from stwhas_api_client import StwHasApiClient
from stwhas_api_client.stwhaseexvalue import StwHasEexValue

_LOGGER = logging.getLogger(__name__)


class Marketprice:
    UOM_CT_PER_kWh = "ct/kWh"

    def __init__(self, duration, data: StwHasEexValue):
        self._start_time = data.datetime
        self._end_time = self._start_time + timedelta(minutes=duration)
        self._price_ct_per_kwh = data.price

    def __repr__(self):
        return f"{self.__class__.__name__}(start: {self._start_time.isoformat()}, end: {self._end_time.isoformat()}, marketprice: {self._price_ct_per_kwh} {self.UOM_CT_PER_kWh})"  # noqa: E501

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    def set_end_time(self, end_time):
        self._end_time = end_time

    @property
    def price_eur_per_mwh(self):
        return round(self._price_ct_per_kwh * 10, 2)

    @property
    def price_ct_per_kwh(self):
        return self._price_ct_per_kwh


class stwhas:
    MARKET_AREAS = ("Haßfurt",)

    def __init__(self, username, password, market_area):
        self.api = StwHasApiClient(username, password)

    @property
    def name(self):
        return "Stadtwerk Haßfurt API"

    @property
    def market_area(self):
        return "DE"

    @property
    def duration(self):
        return self._duration

    @property
    def currency(self):
        return "EUR"

    @property
    def marketdata(self):
        return self._marketdata

    async def fetch(self):
        # self.api.login()
        # await self.api.eexData()
        data = await self._fetch_data(self.URL)
        self._duration = data["interval"]
        assert data["unit"].lower() == Marketprice.UOM_CT_PER_kWh.lower()
        marketdata = self._extract_marketdata(data["data"])
        # override duration and compress data
        self._duration = 60
        self._marketdata = self._compress_marketdata(marketdata)

    async def _fetch_data(self, url):
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _extract_marketdata(self, data):
        entries = []
        for entry in data:
            entries.append(Marketprice(self._duration, entry))
        return entries

    def _compress_marketdata(self, data):
        entries = []
        start = None
        for entry in data:
            if start == None:
                start = entry
                continue
            is_price_equal = start.price_ct_per_kwh == entry.price_ct_per_kwh
            is_continuation = start.end_time == entry.start_time
            max_start_time = start.start_time + timedelta(minutes=self._duration)
            is_same_hour = entry.start_time < max_start_time

            if is_price_equal & is_continuation & is_same_hour:
                start.set_end_time(entry.end_time)
            else:
                entries.append(start)
                start = entry
        if start != None:
            entries.append(start)
        return entries
