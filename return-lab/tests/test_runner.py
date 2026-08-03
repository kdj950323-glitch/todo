"""매수/매도 수익률 계산 로직 유닛테스트. 네트워크 의존 없이 합성 가격 데이터로만 검증."""
import datetime as dt

import pandas as pd
import pytest

from backtest.runner import compute_cagr, run_lump_sum_on_prices, snap_trading_day


def _price_df() -> pd.DataFrame:
    # 2024-01-01(월)~2024-01-31, 주말 제외 영업일만. 종가는 100에서 시작해 매일 1씩 상승.
    index = pd.bdate_range("2024-01-01", "2024-01-31")
    close = [100.0 + i for i in range(len(index))]
    return pd.DataFrame({"Close": close}, index=index)


def test_snap_trading_day_forward_on_weekend_moves_to_next_business_day():
    df = _price_df()
    snap = snap_trading_day(df.index, dt.date(2024, 1, 6), "forward")  # 토요일
    assert snap.adjusted is True
    assert snap.resolved.date() == dt.date(2024, 1, 8)  # 월요일


def test_snap_trading_day_backward_on_weekend_moves_to_prev_business_day():
    df = _price_df()
    snap = snap_trading_day(df.index, dt.date(2024, 1, 6), "backward")  # 토요일
    assert snap.adjusted is True
    assert snap.resolved.date() == dt.date(2024, 1, 5)  # 금요일


def test_snap_trading_day_out_of_range_raises():
    df = _price_df()
    with pytest.raises(ValueError):
        snap_trading_day(df.index, dt.date(2024, 3, 1), "forward")


def test_compute_cagr_basic():
    # 1년 만에 원금이 2배가 되면 CAGR은 100%
    cagr = compute_cagr(1_000_000, 2_000_000, 1.0)
    assert cagr == pytest.approx(100.0, abs=0.01)


def test_compute_cagr_invalid_years_returns_none():
    assert compute_cagr(1_000_000, 2_000_000, 0) is None


def test_run_lump_sum_profit_and_cagr():
    df = _price_df()
    result = run_lump_sum_on_prices(df, dt.date(2024, 1, 2), dt.date(2024, 1, 31), 1_000_000)
    assert result.buy_price < result.sell_price
    assert result.return_pct > 0
    assert result.profit_loss > 0
    assert result.shares == pytest.approx(1_000_000 / result.buy_price)
    assert result.final_value == pytest.approx(result.shares * result.sell_price)


def test_run_lump_sum_buy_after_sell_raises():
    df = _price_df()
    with pytest.raises(ValueError):
        run_lump_sum_on_prices(df, dt.date(2024, 1, 31), dt.date(2024, 1, 2), 1_000_000)


def test_run_lump_sum_non_positive_amount_raises():
    df = _price_df()
    with pytest.raises(ValueError):
        run_lump_sum_on_prices(df, dt.date(2024, 1, 2), dt.date(2024, 1, 31), 0)
