"""미국 주식/ETF 시세 데이터 레이어 (yfinance 기반).

yfinance는 Yahoo Finance의 비공식 클라이언트로 간헐적 차단/레이트리밋이 발생할 수 있다.
disk_cache + retry로 감싸 캐시 폴백을 보장한다.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import yfinance as yf

from core.cache import disk_cache, retry
from core.config import TTL_HISTORICAL, TTL_TODAY
from utils.dates import to_iso


def _ttl_for(end: dt.date) -> int | None:
    return TTL_TODAY if end >= dt.date.today() else TTL_HISTORICAL


@retry(source="yfinance OHLCV")
def _fetch_ohlcv(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(start=to_iso(start), end=to_iso(end + dt.timedelta(days=1)))
    if df.empty:
        raise ValueError("yfinance returned empty OHLCV")
    df.index = df.index.tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def get_ohlcv(ticker: str, start: dt.date, end: dt.date, force_refresh: bool = False) -> pd.DataFrame:
    @disk_cache("us_ohlcv", _ttl_for(end), source="yfinance OHLCV")
    def _get(ticker: str, start_s: str, end_s: str) -> pd.DataFrame:
        return _fetch_ohlcv(ticker, start, end)

    return _get(ticker, to_iso(start), to_iso(end), force_refresh=force_refresh)
