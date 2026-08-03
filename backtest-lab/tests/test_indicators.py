import numpy as np
import pandas as pd

from indicators import momentum, trend, volatility


def test_sma_constant_series():
    s = pd.Series([10.0] * 30)
    result = trend.sma(s, 5)
    assert result.iloc[-1] == 10.0
    assert result.iloc[:4].isna().all()


def test_ema_reacts_faster_than_sma_to_shock():
    s = pd.Series([10.0] * 20 + [20.0] * 5)
    sma20 = trend.sma(s, 20).iloc[-1]
    ema20 = trend.ema(s, 20).iloc[-1]
    assert ema20 > sma20


def test_rsi_monotonic_uptrend_is_high():
    s = pd.Series(np.arange(1, 40, dtype=float))
    r = momentum.rsi(s, window=14)
    assert r.iloc[-1] > 90


def test_rsi_monotonic_downtrend_is_low():
    s = pd.Series(np.arange(40, 1, -1, dtype=float))
    r = momentum.rsi(s, window=14)
    assert r.iloc[-1] < 10


def test_bollinger_mid_equals_sma():
    s = pd.Series(np.random.default_rng(0).normal(100, 5, 60))
    bb = volatility.bollinger_bands(s, window=20)
    sma20 = trend.sma(s, 20)
    pd.testing.assert_series_equal(bb["Mid"], sma20, check_names=False)
    valid = bb.dropna()
    assert (valid["Upper"] >= valid["Mid"]).all()
    assert (valid["Lower"] <= valid["Mid"]).all()


def test_macd_histogram_is_macd_minus_signal():
    s = pd.Series(np.random.default_rng(1).normal(100, 2, 100).cumsum())
    macd_df = trend.macd(s)
    diff = macd_df["MACD"] - macd_df["Signal"]
    pd.testing.assert_series_equal(macd_df["Histogram"], diff, check_names=False)
