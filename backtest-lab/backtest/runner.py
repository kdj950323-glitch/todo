"""주식 물타기(추가 매수) 계산 핵심 로직.

기존 보유 수량/평균단가에 추가 매수를 더했을 때 평균단가가 어떻게 바뀌는지,
현재가를 입력하면 물타기 전/후 손익이 어떻게 달라지는지를 계산한다.
Streamlit 의존이 전혀 없는 순수 함수/데이터클래스로 구성해 유닛테스트가 쉽다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AveragingResult:
    existing_qty: float
    existing_avg_price: float
    add_qty: float
    add_price: float
    add_amount: float
    total_qty: float
    total_invested: float
    new_avg_price: float
    avg_price_change_pct: float  # 음수면 평균단가가 낮아진(물타기 성공) 것
    current_price: float | None
    valuation: float | None
    profit_loss: float | None
    return_pct: float | None
    return_pct_without_averaging: float | None
    breakeven_gap_pct: float | None  # 양수면 손익분기(새 평균단가)까지 더 올라야 함


def compute_averaging_down(
    existing_qty: float,
    existing_avg_price: float,
    add_price: float,
    add_qty: float | None = None,
    add_amount: float | None = None,
    current_price: float | None = None,
) -> AveragingResult:
    """add_qty 또는 add_amount 중 하나만 넘기면 된다(둘 다 넘기면 add_qty 우선)."""
    if existing_qty <= 0:
        raise ValueError("기존 보유 수량은 0보다 커야 합니다.")
    if existing_avg_price <= 0:
        raise ValueError("기존 평균 매수단가는 0보다 커야 합니다.")
    if add_price <= 0:
        raise ValueError("추가 매수단가는 0보다 커야 합니다.")

    if add_qty is not None and add_qty > 0:
        resolved_qty = add_qty
        resolved_amount = add_qty * add_price
    elif add_amount is not None and add_amount > 0:
        resolved_amount = add_amount
        resolved_qty = add_amount / add_price
    else:
        raise ValueError("추가 매수 수량 또는 금액 중 하나는 0보다 커야 합니다.")

    total_qty = existing_qty + resolved_qty
    total_invested = existing_qty * existing_avg_price + resolved_amount
    new_avg_price = total_invested / total_qty
    avg_price_change_pct = (new_avg_price - existing_avg_price) / existing_avg_price * 100

    valuation = profit_loss = return_pct = return_pct_without_averaging = breakeven_gap_pct = None
    if current_price is not None and current_price > 0:
        valuation = total_qty * current_price
        profit_loss = valuation - total_invested
        return_pct = profit_loss / total_invested * 100
        return_pct_without_averaging = (current_price - existing_avg_price) / existing_avg_price * 100
        breakeven_gap_pct = (new_avg_price - current_price) / current_price * 100

    return AveragingResult(
        existing_qty=existing_qty,
        existing_avg_price=existing_avg_price,
        add_qty=resolved_qty,
        add_price=add_price,
        add_amount=resolved_amount,
        total_qty=total_qty,
        total_invested=total_invested,
        new_avg_price=new_avg_price,
        avg_price_change_pct=avg_price_change_pct,
        current_price=current_price if current_price and current_price > 0 else None,
        valuation=valuation,
        profit_loss=profit_loss,
        return_pct=return_pct,
        return_pct_without_averaging=return_pct_without_averaging,
        breakeven_gap_pct=breakeven_gap_pct,
    )
