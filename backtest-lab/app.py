"""주식/ETF/코인 매수·매도 수익률 계산기 — "이 날 사서 이 날 팔았으면 수익률이 얼마인가"를
국내 주식·ETF, 미국 주식·ETF, 코인 대상으로 계산하는 단일 페이지 Streamlit 앱.
LLM을 사용하지 않으며, 결과 요약은 계산된 수치를 고정 규칙 템플릿에 대입해 생성한다.
투자 조언이 아니다.
"""
from __future__ import annotations

import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from backtest.report import build_report
from backtest.runner import run_lump_sum
from core.config import (
    DEFAULT_CRYPTO_TICKER,
    DEFAULT_KR_TICKER,
    DEFAULT_US_TICKER,
    POPULAR_CRYPTO_TICKERS,
    POPULAR_KR_TICKERS,
    POPULAR_US_TICKERS,
)
from core.errors import DataSourceUnavailable, show_data_error

st.set_page_config(page_title="매수·매도 수익률 계산기 | 주식·ETF·코인", page_icon="🧪", layout="wide")
st.title("🧪 매수·매도 수익률 계산기")
st.caption("이 날 사서 이 날 팔았으면 수익률이 얼마였을지 계산 — 규칙 기반 계산, 투자 조언 아님")


def _ticker_input(asset_label: str, session_key: str, popular: dict[str, str], default: str, help_text: str) -> str:
    """인기 종목 퀵 선택 + 직접 입력 텍스트박스. 자산군별로 독립된 세션 키를 써서 값이 섞이지 않게 한다."""
    quick_pick_key = f"{session_key}_quick_pick"

    def _apply_quick_pick():
        pick = st.session_state[quick_pick_key]
        if pick != "직접 입력":
            st.session_state[session_key] = pick.split(" ")[0]

    st.selectbox(
        "인기 종목 (선택 시 아래 입력창에 자동 반영)",
        ["직접 입력"] + [f"{t} ({name})" for t, name in popular.items()],
        key=quick_pick_key,
        on_change=_apply_quick_pick,
    )
    return st.text_input(
        asset_label, value=st.session_state.get(session_key, default), key=session_key, help=help_text
    )


with st.sidebar:
    st.header("설정")
    asset_class = st.radio("자산군", ["국내 주식/ETF", "미국 주식/ETF", "코인"], key="asset_class")

    if asset_class == "국내 주식/ETF":
        ticker = _ticker_input(
            "종목/ETF 코드", "ticker_kr", POPULAR_KR_TICKERS, DEFAULT_KR_TICKER,
            "6자리 코드 (예: 삼성전자 005930, KODEX 200 069500)",
        )
    elif asset_class == "미국 주식/ETF":
        ticker = _ticker_input(
            "티커", "ticker_us", POPULAR_US_TICKERS, DEFAULT_US_TICKER,
            "예: 애플 AAPL, S&P500 ETF SPY",
        )
    else:
        ticker = _ticker_input(
            "티커", "ticker_crypto", POPULAR_CRYPTO_TICKERS, DEFAULT_CRYPTO_TICKER,
            "yfinance 표기 (예: BTC-USD, ETH-USD)",
        )

    today = dt.date.today()
    buy_date = st.date_input("매수일", value=today - dt.timedelta(days=365), key="buy_date")
    sell_date = st.date_input("매도일", value=today, key="sell_date")
    invest_amount = st.number_input("투자금액", min_value=10_000, value=10_000_000, step=100_000)

if st.button("▶ 수익률 계산", type="primary"):
    if buy_date >= sell_date:
        st.warning("매수일은 매도일보다 이전이어야 합니다.")
        st.stop()
    try:
        with st.spinner("계산 중..."):
            result = run_lump_sum(
                asset_class,
                ticker.strip().upper() if asset_class != "국내 주식/ETF" else ticker.strip(),
                buy_date, sell_date, invest_amount,
            )
    except DataSourceUnavailable as e:
        show_data_error(st, e)
        st.stop()
    except ValueError as e:
        st.warning(str(e))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("수익률", f"{result.return_pct:+.2f}%")
    m2.metric("손익금액", f"{result.profit_loss:+,.0f}")
    m3.metric("평가금액", f"{result.final_value:,.0f}")
    m4.metric("연환산수익률(CAGR)", f"{result.cagr_pct:.2f}%" if result.cagr_pct is not None else "-")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result.price_df.index, y=result.price_df["Close"], name="종가", line=dict(color="#2563EB")))
    fig.add_trace(go.Scatter(
        x=[result.buy_snap.resolved], y=[result.buy_price], mode="markers+text",
        marker=dict(color="#10B981", size=12), text=["매수"], textposition="top center", name="매수",
    ))
    fig.add_trace(go.Scatter(
        x=[result.sell_snap.resolved], y=[result.sell_price], mode="markers+text",
        marker=dict(color="#EF4444", size=12), text=["매도"], textposition="top center", name="매도",
    ))
    fig.update_layout(title="가격 차트", height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 결과 요약 (규칙 기반)")
    for line in build_report(result):
        st.markdown(f"- {line}")

    st.caption("⚠️ 수수료·세금·배당은 계산에 포함되지 않습니다. 과거 수익률이 미래 수익을 보장하지 않으며, 투자 조언이 아닙니다.")
