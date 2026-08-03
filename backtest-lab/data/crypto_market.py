"""코인(암호화폐) 시세 데이터 레이어 (yfinance 기반).

yfinance는 BTC-USD, ETH-USD 같은 `<심볼>-USD` 티커로 코인 일봉 데이터를 무료 제공한다
(별도 거래소 API 키 불필요). 미국 주식과 동일한 클라이언트/캐시 정책을 그대로 사용한다.
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


@retry(source="yfinance 코인 OHLCV")
def _fetch_ohlcv(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(start=to_iso(start), end=to_iso(end + dt.timedelta(days=1)))
    if df.empty:
        raise ValueError("yfinance returned empty crypto OHLCV")
    df.index = df.index.tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def get_ohlcv(ticker: str, start: dt.date, end: dt.date, force_refresh: bool = False) -> pd.DataFrame:
    """일봉 OHLCV(USD 기준). 코인은 연중무휴 거래라 국내/미국 증시보다 데이터 밀도가 높다."""

    @disk_cache("crypto_ohlcv", _ttl_for(end), source="yfinance 코인 OHLCV")
    def _get(ticker: str, start_s: str, end_s: str) -> pd.DataFrame:
        return _fetch_ohlcv(ticker, start, end)

    return _get(ticker, to_iso(start), to_iso(end), force_refresh=force_refresh)
