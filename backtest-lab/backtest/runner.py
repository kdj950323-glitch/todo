"""백테스트 실행기: 자산군별 데이터 조회 -> backtesting.py 실행 -> stats/trades 반환."""
from __future__ import annotations

import datetime as dt

import pandas as pd
from backtesting import Backtest

from backtest.strategies import STRATEGY_REGISTRY
from data import crypto_market, kr_market, us_market

_DATA_MODULES = {
    "국내 주식/ETF": kr_market,
    "미국 주식/ETF": us_market,
    "코인": crypto_market,
}


def run_backtest(
    asset_class: str,
    ticker: str,
    start: dt.date,
    end: dt.date,
    strategy_name: str,
    params: dict | None = None,
    cash: float = 10_000_000,
    commission: float = 0.0015,
) -> tuple[pd.Series, pd.DataFrame, Backtest]:
    """asset_class는 _DATA_MODULES의 키, strategy_name은 STRATEGY_REGISTRY의 키.
    params는 전략 클래스 속성을 덮어쓸 값.
    """
    params = params or {}
    strategy_cls = STRATEGY_REGISTRY[strategy_name]
    data_module = _DATA_MODULES[asset_class]

    df = data_module.get_ohlcv(ticker, start, end)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if len(df) < 30:
        raise ValueError("백테스트에 필요한 최소 데이터(30 거래일)가 부족합니다.")

    bt = Backtest(df, strategy_cls, cash=cash, commission=commission, exclusive_orders=True)
    stats = bt.run(**params)
    trades = stats["_trades"]
    return stats, trades, bt
