"""변동성 지표: 볼린저밴드. 순수 pandas 구현."""
from __future__ import annotations

import pandas as pd


def bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    bandwidth = (upper - lower) / mid
    return pd.DataFrame({"Mid": mid, "Upper": upper, "Lower": lower, "Bandwidth": bandwidth})
