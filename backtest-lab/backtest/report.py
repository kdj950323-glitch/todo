"""물타기 계산 결과(AveragingResult)를 규칙 기반 템플릿 문장으로 요약. LLM 미사용."""
from __future__ import annotations

from backtest.runner import AveragingResult


def build_report(result: AveragingResult) -> list[str]:
    """텍스트 문단 리스트 반환 (각 문단은 계산된 수치를 고정 템플릿에 대입한 결과)."""
    direction = "낮아졌습니다" if result.avg_price_change_pct < 0 else "높아졌습니다"
    lines = [
        f"기존 {result.existing_qty:,.4f}주(평단 {result.existing_avg_price:,.2f}) + "
        f"추가 매수 {result.add_qty:,.4f}주(단가 {result.add_price:,.2f}, {result.add_amount:,.0f}) "
        f"= 총 {result.total_qty:,.4f}주.",
        f"평균 매수단가는 {result.existing_avg_price:,.2f} → {result.new_avg_price:,.2f}로 "
        f"{abs(result.avg_price_change_pct):.2f}% {direction}.",
        f"총 투자원금은 {result.total_invested:,.0f}입니다.",
    ]

    if result.current_price is not None:
        lines.append(
            f"현재가 {result.current_price:,.2f} 기준 평가금액은 {result.valuation:,.0f}이며, "
            f"손익은 {result.profit_loss:+,.0f}({result.return_pct:+.2f}%)입니다."
        )
        diff = result.return_pct - result.return_pct_without_averaging
        comp = "개선" if diff > 0 else "악화" if diff < 0 else "동일"
        lines.append(
            f"물타기를 하지 않았다면 손익률은 {result.return_pct_without_averaging:+.2f}%였을 것이며, "
            f"물타기 이후 손익률은 {result.return_pct:+.2f}%로 {abs(diff):.2f}%p {comp}되었습니다."
        )
        if result.breakeven_gap_pct > 0:
            lines.append(f"새 평균단가(손익분기)까지는 {result.breakeven_gap_pct:.2f}% 추가 상승이 필요합니다.")
        else:
            lines.append(f"현재가가 이미 새 평균단가보다 {abs(result.breakeven_gap_pct):.2f}% 높아 평가이익 구간입니다.")

    return lines
