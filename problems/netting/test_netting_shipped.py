"""
Pre-shipped tests.

These tests were passing when the codebase was handed to you.
They do not constitute a complete test suite.
"""

import pytest
from datetime import date

from question import (
    BookError,
    Trade,
    TradeBook,
    NettingRun,
    _build_obligation,
    _is_in_scope,
    _net_signed,
    net_obligations,
)


# ---------------------------------------------------------------------------
# Trade creation
# ---------------------------------------------------------------------------


class TestShippedTradeCreation:
    def test_add_trade_returns_trade_with_given_fields(self):
        book = TradeBook(cutoff_date=date(2026, 10, 20))
        t = book.add_trade("ALPHA", "USD", "buy", 500_000, date(2026, 10, 15))
        assert t.counterparty == "ALPHA"
        assert t.currency == "USD"
        assert t.direction == "buy"
        assert t.notional_cents == 500_000
        assert t.settlement_date == date(2026, 10, 15)

    def test_add_trade_rejects_negative_notional(self):
        book = TradeBook(cutoff_date=date(2026, 10, 20))
        with pytest.raises(BookError):
            book.add_trade("ALPHA", "USD", "buy", -1, date(2026, 10, 15))

    def test_add_trade_rejects_unknown_direction(self):
        book = TradeBook(cutoff_date=date(2026, 10, 20))
        with pytest.raises(BookError):
            book.add_trade("ALPHA", "USD", "hold", 100_000, date(2026, 10, 15))


# ---------------------------------------------------------------------------
# Book locking
# ---------------------------------------------------------------------------


class TestShippedBookLocking:
    def test_lock_sets_is_locked_flag(self):
        book = TradeBook(cutoff_date=date(2026, 10, 20))
        assert book.is_locked is False
        book.lock()
        assert book.is_locked is True

    def test_lock_sets_locked_trades(self):
        book = TradeBook(cutoff_date=date(2026, 10, 20))
        book.add_trade("ALPHA", "USD", "buy", 300_000, date(2026, 10, 15))
        book.lock()
        assert book.locked_trades is not None

    def test_locking_twice_raises_book_error(self):
        book = TradeBook(cutoff_date=date(2026, 10, 20))
        book.lock()
        with pytest.raises(BookError):
            book.lock()


# ---------------------------------------------------------------------------
# Scope filter (cases chosen to avoid the cutoff-day boundary)
# ---------------------------------------------------------------------------


class TestShippedInScope:
    def test_trade_before_cutoff_is_in_scope(self):
        cutoff = date(2026, 10, 20)
        trade = Trade("T1", "ALPHA", "USD", "buy", 100_000, date(2026, 10, 15))
        assert _is_in_scope(trade, cutoff) is True

    def test_trade_after_cutoff_is_not_in_scope(self):
        cutoff = date(2026, 10, 20)
        trade = Trade("T1", "ALPHA", "USD", "buy", 100_000, date(2026, 10, 25))
        assert _is_in_scope(trade, cutoff) is False


# ---------------------------------------------------------------------------
# Net computation (buy-only groups to avoid the sell subtraction edge)
# ---------------------------------------------------------------------------


class TestShippedNetSigned:
    def test_all_buy_trades_net_to_their_sum(self, make_trade_group):
        trades = make_trade_group(
            "ALPHA", "USD", date(2026, 10, 15), buys=[300_000, 450_000]
        )
        assert _net_signed(trades) == 750_000

    def test_empty_trade_group_nets_to_zero(self):
        assert _net_signed([]) == 0


# ---------------------------------------------------------------------------
# Obligation construction (positive net only to avoid the abs edge)
# ---------------------------------------------------------------------------


class TestShippedBuildObligation:
    def test_positive_net_produces_receive_obligation(self):
        key = ("ALPHA", "USD", date(2026, 10, 15))
        ob = _build_obligation(key, 400_000)
        assert ob.direction == "receive"

    def test_positive_net_amount_cents_matches_net_value(self):
        key = ("ALPHA", "EUR", date(2026, 10, 16))
        ob = _build_obligation(key, 250_000)
        assert ob.amount_cents == 250_000

    def test_negative_net_produces_pay_obligation(self):
        key = ("BRAVO", "GBP", date(2026, 10, 17))
        ob = _build_obligation(key, -180_000)
        assert ob.direction == "pay"


# ---------------------------------------------------------------------------
# Netting run — all four tests fail with NotImplementedError until
# net_obligations is implemented. That is expected.
# ---------------------------------------------------------------------------


class TestShippedNettingRun:
    def test_single_buy_group_produces_receive_obligation(self, make_book):
        book = make_book()
        book.add_trade("ALPHA", "USD", "buy", 600_000, date(2026, 10, 15))
        book.lock()
        run = net_obligations(book)
        assert isinstance(run, NettingRun)
        assert len(run.obligations) == 1
        assert run.obligations[0].direction == "receive"

    def test_total_receive_equals_sum_of_positive_group_nets(self, make_book):
        book = make_book()
        book.add_trade("ALPHA", "USD", "buy", 400_000, date(2026, 10, 15))
        book.add_trade("BRAVO", "EUR", "buy", 200_000, date(2026, 10, 16))
        book.lock()
        run = net_obligations(book)
        assert run.total_receive_cents == 600_000

    def test_zero_net_group_is_excluded_from_obligations(self, make_book):
        book = make_book()
        book.add_trade("ALPHA", "USD", "buy",  300_000, date(2026, 10, 15))
        book.add_trade("ALPHA", "USD", "sell", 300_000, date(2026, 10, 15))
        book.lock()
        run = net_obligations(book)
        assert len(run.obligations) == 0

    def test_net_obligations_raises_book_error_for_unlocked_book(self, make_book):
        book = make_book()
        book.add_trade("ALPHA", "USD", "buy", 100_000, date(2026, 10, 15))
        with pytest.raises(BookError):
            net_obligations(book)
