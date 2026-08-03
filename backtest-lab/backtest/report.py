"""매수/매도 결과(LumpSumResult)를 규칙 기반 템플릿 문장으로 요약. LLM 미사용."""
from __future__ import annotations

from backtest.runner import LumpSumResult


def _cagr_comment(cagr_pct: float | None) -> str:
    if cagr_pct is None:
        return "보유 기간이 너무 짧아 연환산수익률은 계산하지 않았습니다."
    if cagr_pct >= 15:
        return f"연환산수익률(CAGR)은 {cagr_pct:.1f}%로 높은 편입니다."
    if cagr_pct >= 0:
        return f"연환산수익률(CAGR)은 {cagr_pct:.1f}%입니다."
    return f"연환산수익률(CAGR)은 {cagr_pct:.1f}%로 손실 구간입니다."


def build_report(result: LumpSumResult) -> list[str]:
    """텍스트 문단 리스트 반환 (각 문단은 계산된 수치를 고정 템플릿에 대입한 결과)."""
    lines = [
        f"매수가 {result.buy_price:,.2f} → 매도가 {result.sell_price:,.2f}로, "
        f"수익률은 {result.return_pct:+.2f}%입니다.",
        f"투자금 {result.invested_amount:,.0f} 기준 손익은 {result.profit_loss:+,.0f}이며, "
        f"평가금액은 {result.final_value:,.0f}입니다.",
        f"보유 기간은 {result.holding_days}일({result.holding_years:.2f}년)입니다.",
        _cagr_comment(result.cagr_pct),
    ]
    if result.buy_snap.adjusted:
        lines.append(
            f"매수일이 휴장일이라 다음 거래일({result.buy_snap.resolved.date()})에 체결된 것으로 계산했습니다."
        )
    if result.sell_snap.adjusted:
        lines.append(
            f"매도일이 휴장일이라 직전 거래일({result.sell_snap.resolved.date()})의 종가로 계산했습니다."
        )
    return lines
