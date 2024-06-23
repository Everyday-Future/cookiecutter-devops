"""

Polygon Finance API

Data on Stocks, Options, Crypto, Forex, and Indices

"""
from datetime import timedelta
import logging


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


def weekdays_between(start_date, end_date):
    """Generate all weekdays between start_date and end_date"""
    day = start_date
    while day <= end_date:
        if day.weekday() < 5:  # 0-4 denotes Monday to Friday
            yield day
        day += timedelta(days=1)


"""

St Louis FRED API

https://fred.stlouisfed.org/docs/api/fred/#General_Documentation

"""
from fredapi import Fred
from config import Config


class FredAPI:
    fred = Fred(api_key=Config.FRED_API_KEY)

    @classmethod
    def get_series(cls, series_name='SP500'):
        return cls.fred.get_series(series_name)


"""

World Bank API

https://documents.worldbank.org/en/publication/documents-reports/api

"""


class WorldBankAPI:
    """
    Interface to World Bank Economic Statistics
    """
    @classmethod
    def search(cls, query):
        url = "https://search.worldbank.org/api/v2/wds?format=json&display_title=wind%20energy"
        pass




