"""합성 OHLCV로 각 프리셋 전략이 네트워크 없이 정상 실행되는지 확인하는 스모크 테스트."""
import numpy as np
import pandas as pd
from backtesting import Backtest

from backtest.strategies import STRATEGY_REGISTRY


def _synthetic_ohlcv(n: int = 250, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + rng.normal(0, 1, n).cumsum()
    close = np.clip(close, 10, None)
    high = close + rng.uniform(0, 1, n)
    low = close - rng.uniform(0, 1, n)
    open_ = close + rng.uniform(-0.5, 0.5, n)
    volume = rng.integers(1000, 10000, n)
    index = pd.date_range("2023-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index
    )


def test_all_strategies_run_without_error():
    df = _synthetic_ohlcv()
    for name, strategy_cls in STRATEGY_REGISTRY.items():
        bt = Backtest(df, strategy_cls, cash=10_000_000, commission=0.0015, exclusive_orders=True)
        stats = bt.run()
        assert stats is not None
        assert "Return [%]" in stats
        assert "_equity_curve" in stats
