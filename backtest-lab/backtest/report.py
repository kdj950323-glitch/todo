"""백테스트 결과(stats)를 규칙 기반 템플릿 문장으로 요약. LLM 미사용."""
from __future__ import annotations

import pandas as pd


def _sharpe_comment(sharpe: float) -> str:
    if pd.isna(sharpe):
        return "샤프비율을 계산할 수 없습니다(거래 없음 또는 변동성 0)."
    if sharpe >= 1.0:
        return f"샤프비율 {sharpe:.2f}로 위험 대비 수익이 양호한 편입니다."
    if sharpe >= 0:
        return f"샤프비율 {sharpe:.2f}로 위험 대비 수익이 보통 수준입니다."
    return f"샤프비율 {sharpe:.2f}로 위험 대비 수익이 저조합니다."


def _mdd_comment(mdd: float) -> str:
    mdd = abs(mdd)
    if mdd >= 30:
        return f"최대낙폭(MDD)이 {mdd:.1f}%로 매우 커서 변동성 감내 능력이 중요합니다."
    if mdd >= 15:
        return f"최대낙폭(MDD)이 {mdd:.1f}%로 다소 큰 편입니다."
    return f"최대낙폭(MDD)이 {mdd:.1f}%로 비교적 양호하게 관리되었습니다."


def _vs_buy_hold_comment(strategy_return: float, buy_hold_return: float) -> str:
    diff = strategy_return - buy_hold_return
    if diff > 0:
        return f"단순 보유(Buy & Hold, {buy_hold_return:.1f}%) 대비 {diff:.1f}%p 초과 수익을 기록했습니다."
    if diff < 0:
        return f"단순 보유(Buy & Hold, {buy_hold_return:.1f}%) 대비 {abs(diff):.1f}%p 낮은 수익을 기록했습니다."
    return "단순 보유(Buy & Hold)와 동일한 수익률입니다."


def build_report(stats: pd.Series) -> list[str]:
    """텍스트 문단 리스트 반환 (각 문단은 계산된 수치를 고정 템플릿에 대입한 결과)."""
    n_trades = int(stats.get("# Trades", 0))
    lines = [
        f"기간 수익률은 {stats['Return [%]']:.1f}%이며, 총 {n_trades}회 거래가 발생했습니다.",
        _vs_buy_hold_comment(stats["Return [%]"], stats["Buy & Hold Return [%]"]),
        _sharpe_comment(stats.get("Sharpe Ratio", float("nan"))),
        _mdd_comment(stats.get("Max. Drawdown [%]", 0.0)),
    ]
    if n_trades > 0:
        win_rate = stats.get("Win Rate [%]", float("nan"))
        lines.append(f"승률은 {win_rate:.1f}%이며, 평균 거래 손익은 {stats.get('Avg. Trade [%]', float('nan')):.2f}%입니다.")
    else:
        lines.append("해당 기간 동안 진입 조건이 충족되지 않아 실제 거래가 발생하지 않았습니다.")
    return lines
