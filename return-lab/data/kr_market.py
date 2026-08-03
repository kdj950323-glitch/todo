"""국내(KRX) 시세 데이터 레이어 (pykrx 기반, FinanceDataReader 폴백).

pykrx는 KRX 웹사이트를 스크레이핑하는 비공식 라이브러리이므로 예고 없이 깨질 수 있다.
disk_cache + retry로 감싸 캐시된 값으로의 안전한 폴백을 보장한다.
"""
from __future__ import annotations

import datetime as dt

import FinanceDataReader as fdr
import pandas as pd
from pykrx import stock

from core.cache import disk_cache, retry
from core.config import TTL_HISTORICAL, TTL_TODAY
from utils.dates import to_yyyymmdd

_OHLCV_COLUMNS = {
    "시가": "Open",
    "고가": "High",
    "저가": "Low",
    "종가": "Close",
    "거래량": "Volume",
}


def _ttl_for(end: dt.date) -> int | None:
    """조회 종료일이 오늘이면 짧은 TTL, 과거 마감 데이터면 무기한 캐시."""
    return TTL_TODAY if end >= dt.date.today() else TTL_HISTORICAL


@retry(source="pykrx OHLCV")
def _fetch_ohlcv_pykrx(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    df = stock.get_market_ohlcv_by_date(to_yyyymmdd(start), to_yyyymmdd(end), ticker)
    if df.empty:
        raise ValueError("pykrx returned empty OHLCV")
    return df.rename(columns=_OHLCV_COLUMNS)[["Open", "High", "Low", "Close", "Volume"]]


def get_ohlcv(ticker: str, start: dt.date, end: dt.date, force_refresh: bool = False) -> pd.DataFrame:
    """일봉 OHLCV. pykrx 실패 시 FinanceDataReader로 폴백."""

    @disk_cache("kr_ohlcv", _ttl_for(end), source="pykrx/FDR OHLCV")
    def _get(ticker: str, start_s: str, end_s: str) -> pd.DataFrame:
        try:
            return _fetch_ohlcv_pykrx(ticker, start, end)
        except Exception:
            df = fdr.DataReader(ticker, start, end)
            return df[["Open", "High", "Low", "Close", "Volume"]]

    return _get(ticker, to_yyyymmdd(start), to_yyyymmdd(end), force_refresh=force_refresh)


@disk_cache("kr_ticker_name", TTL_TODAY, source="pykrx 종목명")
@retry(source="pykrx 종목명")
def get_ticker_name(ticker: str) -> str:
    name = stock.get_market_ticker_name(ticker)
    if not name:
        raise ValueError("empty ticker name")
    return name
