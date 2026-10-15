"""
Shared pytest fixtures for the netting test suite.

Import these in any test file by declaring them as parameters — pytest
injects them automatically.

    def test_something(make_book, make_trade_group):
        book = make_book()
        book.add_trade("ALPHA", "USD", "buy", 500_000, date(2026, 10, 15))
"""

import uuid
from datetime import date

import pytest

from question import Trade, TradeBook

DEFAULT_CUTOFF = date(2026, 10, 20)


@pytest.fixture
def fresh_book():
    """A TradeBook with the default cutoff date and no trades."""
    return TradeBook(cutoff_date=DEFAULT_CUTOFF)


@pytest.fixture
def make_book():
    """
    Factory that creates a TradeBook with a controlled cutoff and ID source.

    Usage::

        def test_example(make_book):
            book = make_book()
            book.add_trade("ALPHA", "USD", "buy", 500_000, date(2026, 10, 15))
    """
    def _factory(cutoff=DEFAULT_CUTOFF, id_source=None):
        if id_source is None:
            id_source = lambda: str(uuid.uuid4())
        return TradeBook(cutoff_date=cutoff, id_source=id_source)

    return _factory


@pytest.fixture
def make_trade_group():
    """
    Build a list of Trade objects sharing a netting key from explicit notionals.

    Useful for testing _net_signed and _build_obligation directly.

    Usage::

        def test_example(make_trade_group):
            trades = make_trade_group(
                "ALPHA", "USD", date(2026, 10, 15), buys=[500_000]
            )
    """
    def _factory(counterparty, currency, settlement_date, buys=(), sells=()):
        trades = []
        n_id = 0
        for notional in buys:
            trades.append(Trade(
                id=f"T{n_id:04d}",
                counterparty=counterparty,
                currency=currency,
                direction="buy",
                notional_cents=notional,
                settlement_date=settlement_date,
            ))
            n_id += 1
        for notional in sells:
            trades.append(Trade(
                id=f"T{n_id:04d}",
                counterparty=counterparty,
                currency=currency,
                direction="sell",
                notional_cents=notional,
                settlement_date=settlement_date,
            ))
            n_id += 1
        return trades

    return _factory
