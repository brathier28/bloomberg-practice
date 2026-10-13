"""
Shipped tests for the FX desk.

These tests pass against the delivered code. Tests in TestShippedSettlementReport
fail with NotImplementedError because plan_settlement is not yet implemented.
"""
import pytest

from question import (
    ConversionRequest,
    Desk,
    DeskError,
    Session,
    Settlement,
    SettlementReport,
    _compute_usd_cost,
    _get_spread,
    _settle_requests,
    plan_settlement,
)


class TestSubmit:
    def test_submit_stores_participant(self, desk):
        req = desk.submit("Alice", "EURUSD", 500_000)
        assert req.participant == "Alice"

    def test_submit_stores_pair(self, desk):
        req = desk.submit("Alice", "EURUSD", 500_000)
        assert req.pair == "EURUSD"

    def test_submit_stores_notional(self, desk):
        req = desk.submit("Alice", "EURUSD", 500_000)
        assert req.notional_cents == 500_000


class TestClose:
    def test_close_returns_session_with_correct_seed(self, desk):
        session = desk.close()
        assert session.seed_cents == 10_000_000

    def test_close_session_contains_submitted_requests(self, desk):
        desk.submit("Alice", "EURUSD", 500_000)
        desk.submit("Bob", "GBPUSD", 3_000_000)
        session = desk.close()
        assert len(session.requests) == 2

    def test_close_rates_contain_submitted_pair(self, make_desk):
        desk = make_desk(rate_source=lambda pair: 10_842)
        desk.submit("Alice", "EURUSD", 500_000)
        session = desk.close()
        assert "EURUSD" in session.rates


class TestGetSpread:
    def test_small_notional_returns_50_bps(self):
        assert _get_spread(500_000) == 50

    def test_mid_notional_returns_20_bps(self):
        assert _get_spread(5_000_000) == 20

    def test_large_notional_returns_5_bps(self):
        assert _get_spread(15_000_000) == 5


class TestComputeUsdCost:
    def test_cost_with_evenly_divisible_product(self):
        # 100_000 * 10_050 = 1_005_000_000; / or // → 100_500
        assert _compute_usd_cost(100_000, 10_000, 50) == 100_500

    def test_cost_scales_with_notional(self):
        assert _compute_usd_cost(200_000, 10_000, 50) > _compute_usd_cost(
            100_000, 10_000, 50
        )


class TestSettleRequests:
    def test_single_request_produces_one_settlement(self, make_session):
        req = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
        session = make_session(requests=(req,), rates={"EURUSD": 10_000})
        result = _settle_requests(session.requests, session.rates)
        assert len(result) == 1

    def test_two_requests_with_unique_pairs_produce_two_settlements(
        self, make_session
    ):
        r1 = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
        r2 = ConversionRequest("id2", "Alice", "GBPUSD", 500_000)
        session = make_session(
            requests=(r1, r2),
            rates={"EURUSD": 10_000, "GBPUSD": 12_000},
        )
        result = _settle_requests(session.requests, session.rates)
        assert len(result) == 2

    def test_settlement_preserves_participant_name(self, make_session):
        req = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
        session = make_session(requests=(req,), rates={"EURUSD": 10_000})
        result = _settle_requests(session.requests, session.rates)
        assert result[0].participant == "Alice"


class TestShippedSettlementReport:
    def test_plan_settlement_empty_session(self, make_session):
        session = make_session(requests=(), rates={})
        report = plan_settlement(session)
        assert report.total_usd_cents == 0

    def test_plan_settlement_single_request(self, make_session):
        req = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
        session = make_session(requests=(req,), rates={"EURUSD": 10_842})
        report = plan_settlement(session)
        assert len(report.settlements) == 1

    def test_plan_settlement_two_requests_produce_two_settlements(
        self, make_session
    ):
        r1 = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
        r2 = ConversionRequest("id2", "Bob", "GBPUSD", 3_000_000)
        session = make_session(
            requests=(r1, r2),
            rates={"EURUSD": 10_842, "GBPUSD": 12_650},
        )
        report = plan_settlement(session)
        assert len(report.settlements) == 2

    def test_plan_settlement_worked_example(self, make_session):
        r1 = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
        r2 = ConversionRequest("id2", "Bob", "EURUSD", 2_000_000)
        session = make_session(
            requests=(r1, r2),
            seed_cents=10_000_000,
            rates={"EURUSD": 10_842},
        )
        report = plan_settlement(session)
        assert report.total_usd_cents == 2_717_000
        assert report.rollover_cents == 7_283_000
