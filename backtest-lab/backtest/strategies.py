"""프리셋 백테스트 전략 (backtesting.py 기반). 자체 구현 indicators/*를 self.I()로 감싸 재사용."""
from __future__ import annotations

import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover

from indicators import momentum, trend, volatility


class SmaCrossStrategy(Strategy):
    """단기/장기 이동평균 골든크로스 매수, 데드크로스 청산."""

    short_window = 20
    long_window = 60

    def init(self):
        close = pd.Series(self.data.Close)
        self.sma_short = self.I(lambda x: trend.sma(pd.Series(x), self.short_window).values, close)
        self.sma_long = self.I(lambda x: trend.sma(pd.Series(x), self.long_window).values, close)

    def next(self):
        if crossover(self.sma_short, self.sma_long):
            self.buy()
        elif crossover(self.sma_long, self.sma_short):
            self.position.close()


class RsiReversionStrategy(Strategy):
    """RSI 과매도 진입 시 매수, 과매수 진입 시 청산 (역추세 전략)."""

    rsi_window = 14
    oversold = 30
    overbought = 70

    def init(self):
        close = pd.Series(self.data.Close)
        self.rsi = self.I(lambda x: momentum.rsi(pd.Series(x), self.rsi_window).values, close)

    def next(self):
        if self.rsi[-1] < self.oversold and not self.position:
            self.buy()
        elif self.rsi[-1] > self.overbought and self.position:
            self.position.close()


class BollingerReversionStrategy(Strategy):
    """볼린저밴드 하단 이탈 시 매수(과매도 회귀 기대), 중심선 회복 시 청산."""

    window = 20
    num_std = 2.0

    def init(self):
        close = pd.Series(self.data.Close)
        bb = volatility.bollinger_bands(close, self.window, self.num_std)
        self.upper = self.I(lambda: bb["Upper"].values)
        self.mid = self.I(lambda: bb["Mid"].values)
        self.lower = self.I(lambda: bb["Lower"].values)

    def next(self):
        price = self.data.Close[-1]
        if price < self.lower[-1] and not self.position:
            self.buy()
        elif price > self.mid[-1] and self.position:
            self.position.close()


class MacdCrossStrategy(Strategy):
    """MACD 골든크로스 매수, 데드크로스 청산."""

    fast = 12
    slow = 26
    signal = 9

    def init(self):
        close = pd.Series(self.data.Close)
        macd_df = trend.macd(close, self.fast, self.slow, self.signal)
        self.macd_line = self.I(lambda: macd_df["MACD"].values)
        self.signal_line = self.I(lambda: macd_df["Signal"].values)

    def next(self):
        if crossover(self.macd_line, self.signal_line):
            self.buy()
        elif crossover(self.signal_line, self.macd_line):
            self.position.close()


STRATEGY_REGISTRY = {
    "이동평균 골든/데드크로스": SmaCrossStrategy,
    "RSI 과매도/과매수 역추세": RsiReversionStrategy,
    "볼린저밴드 회귀": BollingerReversionStrategy,
    "MACD 크로스": MacdCrossStrategy,
}
