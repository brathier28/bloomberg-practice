"""
Pot Luck — Fundraiser Drawing System

Backend implementation for a tiered charity drawing.  Participants enter
a pool, receive a randomly generated five-digit code, and are matched
against a winning code drawn at close time.  Prizes are distributed
according to the number of positional matches.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPONSOR_AMOUNT_CENTS: int = 1_000_000  # $10,000 sponsor seed
ENTRY_FEE_CENTS: int = 500             # $5 per entry

TIER_PERCENTAGES: Dict[int, int] = {
    5: 100,
    4: 40,
    3: 20,
    2: 5,
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FundraiserError(Exception):
    """Raised for invalid fundraiser operations."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """A single participant entry in the drawing."""

    id: str
    participant: str
    code: str


@dataclass(frozen=True)
class Draw:
    """An immutable record of a closed drawing."""

    winning_code: str
    pot_cents: int
    entries: Tuple[Entry, ...]


@dataclass(frozen=True)
class Payout:
    """A single prize award within a PayoutPlan."""

    entry_id: str
    participant: str
    match_count: int
    amount_cents: int


@dataclass(frozen=True)
class PayoutPlan:
    """The complete result of running plan_payouts on a Draw."""

    payouts: Tuple[Payout, ...]
    awarded_cents: int
    rollover_cents: int


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------


class FundraiserPool:
    """
    Manages the lifecycle of a Pot Luck drawing.

    Usage::

        pool = FundraiserPool()
        e1 = pool.enter("Alice")
        e2 = pool.enter("Bob")
        draw = pool.close_draw()
        plan = plan_payouts(draw)
    """

    def __init__(self, random_source: Optional[Callable[[], float]] = None) -> None:
        """
        Parameters
        ----------
        random_source:
            Callable returning a float in [0, 1).  Defaults to
            ``random.random``.  Inject a deterministic callable in tests.
        """
        if random_source is None:
            import random
            random_source = random.random
        self._random_source = random_source
        self._entries: List[Entry] = []
        self._draw: Optional[Draw] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_code(self) -> str:
        """Return a random five-digit string from the configured source."""
        number = int(self._random_source() * 99_999)
        return str(number)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enter(self, participant: str) -> Entry:
        """
        Register *participant* and return their entry.

        Parameters
        ----------
        participant:
            Display name or identifier for the entrant.

        Returns
        -------
        Entry
            The newly created entry, including a unique id and random code.

        Raises
        ------
        FundraiserError
            If called after the draw has already been closed.
        """
        entry_id = str(uuid.uuid4())
        code = self._generate_code()
        entry = Entry(id=entry_id, participant=participant, code=code)
        self._entries.append(entry)
        return entry

    def close_draw(self) -> Draw:
        """
        Close entries, compute the pot, and generate a winning code.

        The pot equals the $10,000 sponsor seed plus $5 per registered entry.
        The winning code is generated with the same mechanism as entry codes.

        Returns
        -------
        Draw
            A record containing the winning code, pot, and participant snapshot.

        Raises
        ------
        FundraiserError
            If the draw has already been closed.
        """
        if self._draw is not None:
            raise FundraiserError("Draw has already been closed.")

        pot_cents = SPONSOR_AMOUNT_CENTS + len(self._entries) * ENTRY_FEE_CENTS
        winning_code = self._generate_code()

        self._draw = Draw(
            winning_code=winning_code,
            pot_cents=pot_cents,
            entries=self._entries,
        )
        return self._draw

    @property
    def draw(self) -> Optional[Draw]:
        """The closed Draw, or None if the pool is still open."""
        return self._draw


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def count_matches(entry_code: str, winning_code: str) -> int:
    """
    Return the number of matching characters between *entry_code* and
    *winning_code*.

    Parameters
    ----------
    entry_code:
        The code assigned to a participant entry.
    winning_code:
        The code drawn at close time.

    Returns
    -------
    int
        Number of matching characters, 0–5.
    """
    return len(set(entry_code) & set(winning_code))


# ---------------------------------------------------------------------------
# Payout planning
# ---------------------------------------------------------------------------


def plan_payouts(draw: Draw) -> PayoutPlan:
    """
    Compute the prize distribution for a closed draw.

    Tiers are evaluated from 5 down to 2.  Winners within a tier split that
    tier's share of the pot using integer division; any remainder rolls over.
    If any entry achieves a 5-match, only the 5-match tier is paid.

    Parameters
    ----------
    draw:
        A closed Draw as returned by ``FundraiserPool.close_draw()``.

    Returns
    -------
    PayoutPlan
        Complete prize plan including awarded total and rollover amount.
    """

    raise NotImplementedError("plan_payouts is not implemented.")
