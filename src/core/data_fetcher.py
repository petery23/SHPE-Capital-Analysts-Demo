import datetime as dt

import pandas as pd
import requests


BASE_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class DataFetchError(Exception):
    """Raised when Yahoo Finance chart API does not return usable data."""


def _date_to_unix(value: dt.date) -> int:
    if isinstance(value, dt.datetime):
        return int(value.timestamp())
    return int(dt.datetime.combine(value, dt.time.min).timestamp())


def fetch_price_history(
    ticker: str,
    start_date: dt.date,
    end_date: dt.date,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data using Yahoo Finance chart API.

    Unlike yfinance's download helper, this endpoint does not require the crumb
    authentication and works reliably in restricted environments.
    """
    params = {
        "interval": interval,
        "includeAdjustedClose": "true",
        "events": "history",
        "period1": _date_to_unix(start_date),
        # Add one day to include end-date data
        "period2": _date_to_unix(end_date + dt.timedelta(days=1)),
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(
        BASE_CHART_URL.format(ticker=ticker),
        params=params,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    result = payload.get("chart", {}).get("result")
    error = payload.get("chart", {}).get("error")

    if error or not result:
        message = error.get("description") if error else "No result returned"
        raise DataFetchError(f"Yahoo Finance error for {ticker}: {message}")

    chart = result[0]
    timestamps = chart.get("timestamp")
    indicators = chart.get("indicators", {})
    quotes = indicators.get("quote", [{}])[0]
    adj_close = indicators.get("adjclose", [{}])[0].get("adjclose")

    if not timestamps or not quotes:
        raise DataFetchError(f"Missing time series for {ticker}.")

    index = pd.to_datetime(timestamps, unit="s")
    df = pd.DataFrame(quotes, index=index)
    if adj_close:
        df["adjclose"] = adj_close
    else:
        df["adjclose"] = df["close"]

    df = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "adjclose": "Adj Close",
            "volume": "Volume",
        }
    )

    expected = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for col in expected:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[expected]

    df = df.tz_localize(None)
    df = df.sort_index()
    df = df.dropna(subset=["Adj Close"])
    return df

