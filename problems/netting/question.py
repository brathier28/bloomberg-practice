"""
Trade Settlement Netting

Backend for end-of-day bilateral trade netting. Trades are added to a
TradeBook, the book is locked at end-of-day, and net_obligations groups
in-scope trades by (counterparty, currency, settlement_date) to produce
a minimal set of net obligations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BookError(Exception):
    """Raised for invalid trade book operations."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trade:
    """A single bilateral trade recorded in the book."""

    id: str
    counterparty: str
    currency: str
    direction: str        # "buy" or "sell"
    notional_cents: int
    settlement_date: date


@dataclass(frozen=True)
class NetObligation:
    """A single net payment obligation produced by netting."""

    counterparty: str
    currency: str
    settlement_date: date
    amount_cents: int     # always a non-negative integer
    direction: str        # "receive" or "pay"


@dataclass(frozen=True)
class NettingRun:
    """The complete result of a netting computation."""

    obligations: Tuple[NetObligation, ...]
    total_receive_cents: int
    total_pay_cents: int


# ---------------------------------------------------------------------------
# Trade book
# ---------------------------------------------------------------------------


class TradeBook:
    """
    Manages the lifecycle of a trade book for end-of-day netting.

    Usage::

        book = TradeBook(cutoff_date=date(2026, 10, 20))
        book.add_trade("ALPHA", "USD", "buy", 1_200_000, date(2026, 10, 18))
        book.lock()
        run = net_obligations(book)
    """

    def __init__(
        self,
        cutoff_date: date,
        id_source: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._cutoff_date = cutoff_date
        self._id_source = id_source
        self._trades: List[Trade] = []
        self._locked: bool = False
        self._locked_trades: Optional[Tuple[Trade, ...]] = None

    @property
    def cutoff_date(self) -> date:
        """The netting cutoff date (inclusive)."""
        return self._cutoff_date

    @property
    def is_locked(self) -> bool:
        """True if the book has been locked."""
        return self._locked

    @property
    def locked_trades(self) -> Optional[Tuple[Trade, ...]]:
        """The frozen trade snapshot, or None if the book is not yet locked."""
        return self._locked_trades

    def add_trade(
        self,
        counterparty: str,
        currency: str,
        direction: str,
        notional_cents: int,
        settlement_date: date,
    ) -> Trade:
        """
        Add a trade to the book and return it.

        Raises BookError if the book is locked, if direction is not
        ``"buy"`` or ``"sell"``, or if notional_cents is negative.
        """
        if direction not in ("buy", "sell"):
            raise BookError(f"invalid direction: {direction!r}")
        if notional_cents < 0:
            raise BookError("notional_cents must be non-negative")
        trade = Trade(
            id=self._id_source(),
            counterparty=counterparty,
            currency=currency,
            direction=direction,
            notional_cents=notional_cents,
            settlement_date=settlement_date,
        )
        self._trades.append(trade)
        return trade

    def lock(self) -> None:
        """
        Seal the book and record a frozen snapshot of the current trade list.

        The snapshot is an immutable copy taken at this moment; any changes
        to the book's internal trade list after locking must not affect it.

        Raises BookError if the book is already locked.
        """
        if self._locked:
            raise BookError("book is already locked")
        self._locked = True
        self._locked_trades = self._trades


# ---------------------------------------------------------------------------
# Netting helpers
# ---------------------------------------------------------------------------


def _is_in_scope(trade: Trade, cutoff: date) -> bool:
    """
    Return True if trade.settlement_date falls on or before cutoff.

    The cutoff date itself is in scope.
    """
    return trade.settlement_date < cutoff


def _net_signed(trades: List[Trade]) -> int:
    """
    Net a list of same-key trades and return a signed integer.

    Buy trades add to the net; sell trades subtract from it.
    A positive result means we receive; negative means we pay.
    """
    buys = sum(t.notional_cents for t in trades if t.direction == "buy")
    sells = sum(t.notional_cents for t in trades if t.direction == "sell")
    return buys + sells


def _build_obligation(
    key: Tuple[str, str, date],
    net: int,
) -> NetObligation:
    """
    Construct a NetObligation from a netting group key and its signed net.

    amount_cents is always a non-negative integer; direction carries the sign.
    Caller must ensure net is non-zero.
    """
    counterparty, currency, settlement_date = key
    if net > 0:
        return NetObligation(
            counterparty=counterparty,
            currency=currency,
            settlement_date=settlement_date,
            amount_cents=net,
            direction="receive",
        )
    return NetObligation(
        counterparty=counterparty,
        currency=currency,
        settlement_date=settlement_date,
        amount_cents=net,
        direction="pay",
    )


# ---------------------------------------------------------------------------
# Target function
# ---------------------------------------------------------------------------


def net_obligations(book: TradeBook) -> NettingRun:
    """
    Compute net obligations from a locked TradeBook.

    Groups all in-scope trades (settlement_date <= cutoff_date) by
    (counterparty, currency, settlement_date). Within each group, sums buy
    notionals and subtracts sell notionals. Groups that net to zero are
    excluded from the output. Returns a NettingRun with the obligations
    tuple and aggregate receive/pay totals.

    Raises BookError if the book is not locked.
    """
    raise NotImplementedError("net_obligations is not implemented.")
