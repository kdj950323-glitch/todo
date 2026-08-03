"""매수/매도 수익률 계산 핵심 로직.

전략 백테스트가 아니라 "이 날 사서 이 날 팔았으면 수익률이 얼마인가"를 계산한다.
Streamlit/네트워크 의존이 전혀 없는 순수 함수/데이터클래스로 구성해
유닛테스트가 합성 데이터만으로 가능하도록 만든다.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from data import crypto_market, kr_market, us_market

_DATA_MODULES = {
    "국내 주식/ETF": kr_market,
    "미국 주식/ETF": us_market,
    "코인": crypto_market,
}


@dataclass
class DateSnap:
    requested: dt.date
    resolved: pd.Timestamp
    adjusted: bool


def snap_trading_day(available: pd.DatetimeIndex, target: dt.date, direction: str) -> DateSnap:
    """direction="forward": target 이후 첫 거래일. "backward": target 이전 마지막 거래일.

    매수(시작)는 forward, 매도(평가)는 backward로 스냅하는 것이 관례다:
    매수는 시장이 열려야 실행 가능(주말/휴일이면 다음 거래일에 체결),
    매도/평가는 "그 시점 기준 가치"를 묻는 것이므로 직전 종가를 사용한다.
    """
    target_ts = pd.Timestamp(target)
    if direction == "forward":
        candidates = available[available >= target_ts]
        if len(candidates) == 0:
            raise ValueError(f"{target} 이후로 거래 가능한 날짜가 데이터에 없습니다 (데이터 범위를 벗어났습니다).")
        resolved = candidates.min()
    elif direction == "backward":
        candidates = available[available <= target_ts]
        if len(candidates) == 0:
            raise ValueError(f"{target} 이전에 거래 가능한 날짜가 데이터에 없습니다 (상장 전일 수 있습니다).")
        resolved = candidates.max()
    else:
        raise ValueError(f"알 수 없는 방향: {direction}")
    return DateSnap(requested=target, resolved=resolved, adjusted=resolved.date() != target)


def compute_cagr(begin_value: float, end_value: float, years: float) -> float | None:
    """연환산수익률(%). years<=0이거나 begin_value<=0이면 계산 불가로 None."""
    if years <= 0 or begin_value <= 0:
        return None
    return ((end_value / begin_value) ** (1 / years) - 1) * 100


@dataclass
class LumpSumResult:
    buy_snap: DateSnap
    sell_snap: DateSnap
    buy_price: float
    sell_price: float
    shares: float
    invested_amount: float
    final_value: float
    profit_loss: float
    return_pct: float
    holding_days: int
    holding_years: float
    cagr_pct: float | None
    price_df: pd.DataFrame


def run_lump_sum_on_prices(
    price_df: pd.DataFrame, buy_date: dt.date, sell_date: dt.date, invest_amount: float
) -> LumpSumResult:
    """price_df는 DatetimeIndex + 'Close' 컬럼을 가져야 한다."""
    if buy_date >= sell_date:
        raise ValueError("매수일은 매도일보다 이전이어야 합니다.")
    if invest_amount <= 0:
        raise ValueError("투자금액은 0보다 커야 합니다.")

    available = price_df.index
    buy_snap = snap_trading_day(available, buy_date, "forward")
    sell_snap = snap_trading_day(available, sell_date, "backward")
    if sell_snap.resolved <= buy_snap.resolved:
        raise ValueError("매수일과 매도일 사이에 거래일이 없습니다. 날짜 범위를 넓혀주세요.")

    buy_price = float(price_df.loc[buy_snap.resolved, "Close"])
    sell_price = float(price_df.loc[sell_snap.resolved, "Close"])
    if pd.isna(buy_price) or buy_price <= 0 or pd.isna(sell_price) or sell_price <= 0:
        raise ValueError("가격 데이터가 유효하지 않습니다.")

    shares = invest_amount / buy_price
    final_value = shares * sell_price
    profit_loss = final_value - invest_amount
    return_pct = profit_loss / invest_amount * 100
    holding_days = (sell_snap.resolved - buy_snap.resolved).days
    holding_years = holding_days / 365.25
    cagr_pct = compute_cagr(invest_amount, final_value, holding_years)

    return LumpSumResult(
        buy_snap=buy_snap,
        sell_snap=sell_snap,
        buy_price=buy_price,
        sell_price=sell_price,
        shares=shares,
        invested_amount=invest_amount,
        final_value=final_value,
        profit_loss=profit_loss,
        return_pct=return_pct,
        holding_days=holding_days,
        holding_years=holding_years,
        cagr_pct=cagr_pct,
        price_df=price_df,
    )


def run_lump_sum(
    asset_class: str,
    ticker: str,
    buy_date: dt.date,
    sell_date: dt.date,
    invest_amount: float,
    buffer_days: int = 15,
) -> LumpSumResult:
    """asset_class는 _DATA_MODULES의 키. 휴일(설/추석 등)에 대비해 조회 범위를 앞뒤로 넉넉히 넓힌다."""
    data_module = _DATA_MODULES[asset_class]
    today = dt.date.today()
    fetch_start = buy_date - dt.timedelta(days=buffer_days)
    fetch_end = min(sell_date + dt.timedelta(days=buffer_days), today)

    df = data_module.get_ohlcv(ticker, fetch_start, fetch_end)
    df = df.dropna(subset=["Close"])
    if df.empty:
        raise ValueError("해당 티커/기간에 대한 시세 데이터를 찾을 수 없습니다.")

    return run_lump_sum_on_prices(df, buy_date, sell_date, invest_amount)
