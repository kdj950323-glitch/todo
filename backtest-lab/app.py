"""주식/ETF/코인 백테스팅 랩 — 프리셋 전략(이동평균크로스/RSI역추세/볼린저회귀/MACD크로스)
백테스트를 국내 주식·ETF, 미국 주식·ETF, 코인 대상으로 실행하는 단일 페이지 Streamlit 앱.
LLM을 사용하지 않으며, 결과 요약은 계산된 수치를 고정 규칙 템플릿에 대입해 생성한다.
투자 조언이 아니다.
"""
from __future__ import annotations

import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from backtest.report import build_report
from backtest.runner import run_backtest
from backtest.strategies import STRATEGY_REGISTRY
from core.config import (
    DEFAULT_CRYPTO_TICKER,
    DEFAULT_KR_TICKER,
    DEFAULT_US_TICKER,
    POPULAR_CRYPTO_TICKERS,
)
from core.errors import DataSourceUnavailable, show_data_error

st.set_page_config(page_title="백테스팅 랩 | 주식·ETF·코인", page_icon="🧪", layout="wide")
st.title("🧪 백테스팅 랩")
st.caption("주식·ETF·코인 대상 프리셋 전략 백테스팅 — 규칙 기반 계산, 투자 조언 아님")

with st.sidebar:
    st.header("설정")
    asset_class = st.radio("자산군", ["국내 주식/ETF", "미국 주식/ETF", "코인"], key="asset_class")

    if asset_class == "코인":
        def _apply_quick_pick():
            pick = st.session_state["crypto_quick_pick"]
            if pick != "직접 입력":
                st.session_state["ticker_crypto"] = pick.split(" ")[0]

        st.selectbox(
            "인기 코인 (선택 시 티커 자동 입력)",
            ["직접 입력"] + [f"{t} ({name})" for t, name in POPULAR_CRYPTO_TICKERS.items()],
            key="crypto_quick_pick",
            on_change=_apply_quick_pick,
        )
        ticker = st.text_input(
            "티커",
            value=st.session_state.get("ticker_crypto", DEFAULT_CRYPTO_TICKER),
            key="ticker_crypto",
            help="yfinance 표기 (예: BTC-USD, ETH-USD)",
        )
    elif asset_class == "국내 주식/ETF":
        ticker = st.text_input(
            "종목/ETF 코드",
            value=st.session_state.get("ticker_kr", DEFAULT_KR_TICKER),
            key="ticker_kr",
            help="6자리 코드 (예: 삼성전자 005930, KODEX 200 069500)",
        )
    else:
        ticker = st.text_input(
            "티커",
            value=st.session_state.get("ticker_us", DEFAULT_US_TICKER),
            key="ticker_us",
            help="예: 애플 AAPL, S&P500 ETF SPY",
        )

    today = dt.date.today()
    start_date = st.date_input("시작일", value=today - dt.timedelta(days=365 * 2), key="start_date")
    end_date = st.date_input("종료일", value=today, key="end_date")

strategy_name = st.selectbox("전략 선택", list(STRATEGY_REGISTRY.keys()))

params: dict = {}
with st.expander("전략 파라미터 조정", expanded=False):
    if strategy_name == "이동평균 골든/데드크로스":
        params["short_window"] = st.slider("단기 이동평균 기간", 5, 60, 20)
        params["long_window"] = st.slider("장기 이동평균 기간", 20, 200, 60)
    elif strategy_name == "RSI 과매도/과매수 역추세":
        params["rsi_window"] = st.slider("RSI 기간", 5, 30, 14)
        params["oversold"] = st.slider("과매도 기준", 10, 40, 30)
        params["overbought"] = st.slider("과매수 기준", 60, 90, 70)
    elif strategy_name == "볼린저밴드 회귀":
        params["window"] = st.slider("밴드 기간", 10, 60, 20)
        params["num_std"] = st.slider("표준편차 배수", 1.0, 3.0, 2.0, step=0.1)
    elif strategy_name == "MACD 크로스":
        params["fast"] = st.slider("단기 EMA", 5, 20, 12)
        params["slow"] = st.slider("장기 EMA", 20, 50, 26)
        params["signal"] = st.slider("신호선", 5, 15, 9)

col1, col2 = st.columns(2)
cash = col1.number_input("초기 자본", min_value=100_000, value=10_000_000, step=100_000)
commission = col2.number_input("거래 수수료(비율)", min_value=0.0, value=0.0015, step=0.0005, format="%.4f")

if st.button("▶ 백테스트 실행", type="primary"):
    if start_date >= end_date:
        st.warning("시작일은 종료일보다 이전이어야 합니다.")
        st.stop()
    try:
        with st.spinner("백테스트 실행 중..."):
            stats, trades, bt = run_backtest(
                asset_class, ticker.strip().upper() if asset_class != "국내 주식/ETF" else ticker.strip(),
                start_date, end_date, strategy_name, params, cash=cash, commission=commission,
            )
    except DataSourceUnavailable as e:
        show_data_error(st, e)
        st.stop()
    except ValueError as e:
        st.warning(str(e))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 수익률", f"{stats['Return [%]']:.2f}%")
    m2.metric("샤프비율", f"{stats['Sharpe Ratio']:.2f}" if stats["Sharpe Ratio"] == stats["Sharpe Ratio"] else "-")
    m3.metric("최대낙폭(MDD)", f"{stats['Max. Drawdown [%]']:.2f}%")
    m4.metric("거래 횟수", f"{int(stats['# Trades'])}회")

    equity = stats["_equity_curve"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity.index, y=equity["Equity"], name="자산 곡선", line=dict(color="#2563EB")))
    fig.update_layout(title="자산 곡선(Equity Curve)", height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 결과 요약 (규칙 기반)")
    for line in build_report(stats):
        st.markdown(f"- {line}")

    if len(trades) > 0:
        st.markdown("### 거래 내역")
        st.dataframe(trades, use_container_width=True)

    st.caption("⚠️ 과거 백테스트 성과가 미래 수익을 보장하지 않습니다. 투자 조언이 아닙니다.")
