import pytest

from question import (
    ConversionRequest,
    Desk,
    DeskError,
    InvalidInput,
    Session,
    Settlement,
    SettlementReport,
    _compute_usd_cost,
    _get_spread,
    _settle_requests,
    plan_settlement,
)

# Add your tests here.

def make_rate_source(bps: int = 10_842):
    return lambda pair: bps

def test_duplicate_request_not_added():
    desk = Desk(seed_cents=10_000_000, rate_source=make_rate_source())
    desk.submit("Alice", "EURUSD", 500_000)
    desk.submit("Alice", "EURUSD", 500_000)
    session = desk.close()
    assert len(session.requests) == 1


def test_invalid_seed_cents():
    with pytest.raises(InvalidInput):
        Desk(seed_cents=0, rate_source=make_rate_source())


def test_invalid_notional_cents():
    desk = Desk(seed_cents=10_000_000, rate_source=make_rate_source())
    with pytest.raises(InvalidInput):
        desk.submit("Alice", "EURUSD", 0)


def test_spread_tier1_boundary():
    assert _get_spread(999_999) == 50


def test_spread_tier2_boundary():
    assert _get_spread(1_000_000) == 20


def test_spread_tier3_boundary():
    assert _get_spread(10_000_000) == 5


def test_spread_tier2_upper_boundary():
    assert _get_spread(9_999_999) == 20


def test_submit_raises_on_closed_desk():
    desk = Desk(seed_cents=10_000_000, rate_source=make_rate_source())
    desk.close()
    with pytest.raises(DeskError):
        desk.submit("Alice", "EURUSD", 500_000)


def test_close_locks_rates():
    rates = {"EURUSD": 10_842}
    desk = Desk(seed_cents=10_000_000, rate_source=lambda pair: rates[pair])
    desk.submit("Alice", "EURUSD", 500_000)
    session = desk.close()
    rates["EURUSD"] = 99_999  # mutate the source after close
    assert session.rates["EURUSD"] == 10_842


def test_plan_settlement_deduplicates_requests():
    desk = Desk(seed_cents=10_000_000, rate_source=make_rate_source())
    desk.submit("Alice", "EURUSD", 500_000)
    desk.submit("Alice", "EURUSD", 500_000)  # duplicate
    session = desk.close()
    report = plan_settlement(session)
    assert len(report.settlements) == 1


def test_plan_settlement_negative_rollover():
    # seed is tiny so costs exceed it
    desk = Desk(seed_cents=100, rate_source=make_rate_source())
    desk.submit("Alice", "EURUSD", 500_000)
    session = desk.close()
    report = plan_settlement(session)
    assert report.rollover_cents < 0


def test_compute_usd_cost_floors():
    # 500_001 × 10_892 = 5_446_010_892 → floor ÷ 10_000 = 544_601 (not 544_601.0892)
    result = _compute_usd_cost(500_001, 10_842, 50)
    assert result == 544_601
    assert isinstance(result, int)
