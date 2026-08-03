"""주식 물타기(추가 매수) 계산기 — 기존 보유 수량/평균단가에 추가 매수를 더하면
평균단가가 얼마나 낮아지는지, 현재가 기준 손익이 어떻게 달라지는지 계산하는
단일 페이지 Streamlit 앱.
LLM을 사용하지 않으며, 결과 요약은 계산된 수치를 고정 규칙 템플릿에 대입해 생성한다.
투자 조언이 아니다.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from backtest.report import build_report
from backtest.runner import compute_averaging_down

st.set_page_config(page_title="물타기 계산기 | 주식·ETF·코인", page_icon="🧪", layout="wide")
st.title("🧪 주식 물타기 계산기")
st.caption("추가 매수로 평균단가가 얼마나 낮아지는지, 손익이 어떻게 바뀌는지 계산 — 규칙 기반 계산, 투자 조언 아님")

with st.sidebar:
    st.header("기존 보유")
    existing_qty = st.number_input("기존 보유 수량", min_value=0.0001, value=10.0, step=1.0, format="%.4f")
    existing_avg_price = st.number_input("기존 평균 매수단가", min_value=0.01, value=10000.0, step=100.0, format="%.2f")

    st.header("추가 매수")
    add_mode = st.radio("입력 방식", ["수량으로 입력", "금액으로 입력"], key="add_mode")
    add_price = st.number_input("추가 매수단가", min_value=0.01, value=8000.0, step=100.0, format="%.2f")
    add_qty = None
    add_amount = None
    if add_mode == "수량으로 입력":
        add_qty = st.number_input("추가 매수 수량", min_value=0.0001, value=10.0, step=1.0, format="%.4f")
    else:
        add_amount = st.number_input("추가 매수 금액", min_value=0.01, value=80000.0, step=1000.0, format="%.2f")

    st.header("현재가 (선택)")
    current_price_input = st.number_input(
        "현재가", min_value=0.0, value=0.0, step=100.0, format="%.2f",
        help="0으로 두면 손익 비교 없이 평균단가만 계산합니다. 실시간 시세 자동 조회는 지원하지 않습니다.",
    )

if st.button("▶ 계산하기", type="primary"):
    try:
        result = compute_averaging_down(
            existing_qty, existing_avg_price, add_price,
            add_qty=add_qty, add_amount=add_amount,
            current_price=current_price_input if current_price_input > 0 else None,
        )
    except ValueError as e:
        st.warning(str(e))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 보유수량", f"{result.total_qty:,.4f}")
    m2.metric("새 평균단가", f"{result.new_avg_price:,.2f}", f"{result.avg_price_change_pct:+.2f}%")
    m3.metric("총 투자원금", f"{result.total_invested:,.0f}")
    if result.current_price is not None:
        m4.metric("평가손익률", f"{result.return_pct:+.2f}%")
    else:
        m4.metric("평가손익률", "현재가 미입력")

    labels = ["기존 평균단가", "새 평균단가"]
    values = [result.existing_avg_price, result.new_avg_price]
    colors = ["#94A3B8", "#2563EB"]
    if result.current_price is not None:
        labels.append("현재가")
        values.append(result.current_price)
        colors.append("#F59E0B")

    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors, text=[f"{v:,.2f}" for v in values], textposition="outside"))
    fig.update_layout(title="단가 비교", height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 결과 요약 (규칙 기반)")
    for line in build_report(result):
        st.markdown(f"- {line}")

    st.caption("⚠️ 수수료·세금은 계산에 포함되지 않습니다. 투자 조언이 아닙니다.")
