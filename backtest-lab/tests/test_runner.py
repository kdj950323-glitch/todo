"""물타기 계산 로직 유닛테스트. 순수 함수라 네트워크/Streamlit 없이 검증 가능."""
import pytest

from backtest.runner import compute_averaging_down


def test_averaging_down_lowers_average_price_with_qty():
    # 기존 10주 @10,000 + 추가 10주 @8,000 = 20주, 평균 9,000
    result = compute_averaging_down(10, 10_000, add_price=8_000, add_qty=10)
    assert result.total_qty == pytest.approx(20)
    assert result.new_avg_price == pytest.approx(9_000)
    assert result.total_invested == pytest.approx(180_000)
    assert result.avg_price_change_pct == pytest.approx(-10.0)


def test_averaging_down_with_amount_input_matches_qty_input():
    by_qty = compute_averaging_down(10, 10_000, add_price=8_000, add_qty=10)
    by_amount = compute_averaging_down(10, 10_000, add_price=8_000, add_amount=80_000)
    assert by_qty.new_avg_price == pytest.approx(by_amount.new_avg_price)
    assert by_qty.total_qty == pytest.approx(by_amount.total_qty)


def test_averaging_up_raises_average_price():
    result = compute_averaging_down(10, 10_000, add_price=12_000, add_qty=10)
    assert result.new_avg_price == pytest.approx(11_000)
    assert result.avg_price_change_pct == pytest.approx(10.0)


def test_current_price_profit_loss_and_comparison():
    # 기존 10주 @10,000 + 추가 10주 @8,000 = 새 평균 9,000, 현재가 9,500이면 이익
    result = compute_averaging_down(10, 10_000, add_price=8_000, add_qty=10, current_price=9_500)
    assert result.valuation == pytest.approx(190_000)
    assert result.profit_loss == pytest.approx(10_000)
    assert result.return_pct == pytest.approx(10_000 / 180_000 * 100)
    # 물타기 없이 10주만 있었다면: (9500-10000)/10000*100 = -5%
    assert result.return_pct_without_averaging == pytest.approx(-5.0)
    # 물타기 이후 손익률(+5.56%)이 물타기 전(-5%)보다 개선됨
    assert result.return_pct > result.return_pct_without_averaging
    # 현재가(9500)가 새 평균단가(9000)보다 높으므로 이미 손익분기 초과
    assert result.breakeven_gap_pct < 0


def test_current_price_below_new_average_shows_positive_breakeven_gap():
    result = compute_averaging_down(10, 10_000, add_price=8_000, add_qty=10, current_price=8_500)
    assert result.breakeven_gap_pct > 0  # 아직 새 평균단가(9,000)까지 못 올라옴


def test_no_current_price_leaves_pnl_fields_none():
    result = compute_averaging_down(10, 10_000, add_price=8_000, add_qty=10)
    assert result.current_price is None
    assert result.valuation is None
    assert result.profit_loss is None
    assert result.return_pct is None


def test_invalid_existing_qty_raises():
    with pytest.raises(ValueError):
        compute_averaging_down(0, 10_000, add_price=8_000, add_qty=10)


def test_missing_add_qty_and_amount_raises():
    with pytest.raises(ValueError):
        compute_averaging_down(10, 10_000, add_price=8_000)
