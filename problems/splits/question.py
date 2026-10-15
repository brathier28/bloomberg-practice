"""
Tab Split — Group Expense Splitter

Backend for a shared expense tracker.  Participants join a tab; expenses are
recorded and split equally in integer cents.  Remainder cents are distributed
one at a time to participants in join order, earliest first.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SplitTabError(Exception):
    """Raised for invalid tab operations."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Participant:
    """A person registered on a SplitTab."""

    id: str
    name: str


@dataclass(frozen=True)
class Expense:
    """A recorded expense on a SplitTab."""

    id: str
    description: str
    total_cents: int
    participants: Tuple[Participant, ...]


@dataclass(frozen=True)
class Split:
    """One participant's share of an expense."""

    participant_id: str
    participant_name: str
    amount_cents: int


@dataclass(frozen=True)
class SplitPlan:
    """The complete split breakdown for a single expense."""

    splits: Tuple[Split, ...]
    total_distributed: int


# ---------------------------------------------------------------------------
# Tab
# ---------------------------------------------------------------------------


class SplitTab:
    """
    Manages a group tab: participants and recorded expenses.

    Usage::

        tab = SplitTab()
        p1 = tab.add_participant("Alice")
        p2 = tab.add_participant("Bob")
        expense = tab.record_expense("Dinner", 2500)
        plan = plan_splits(expense)
    """

    def __init__(self, id_source: Optional[Callable[[], str]] = None) -> None:
        """
        Parameters
        ----------
        id_source:
            Callable returning a unique string for each expense.  Defaults to
            ``str(uuid.uuid4())``.  Inject a deterministic callable in tests.
        """
        if id_source is None:
            id_source = lambda: str(uuid.uuid4())
        self._id_source = id_source
        self._counter: int = 0
        self._participants: List[Participant] = []
        self._expenses: List[Expense] = []
        self._closed: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_participant(self, name: str) -> Participant:
        """
        Register *name* as a new participant and return their record.

        Each participant receives a unique two-digit zero-padded identifier
        reflecting their join order: first joiner is ``"00"``, second is
        ``"01"``, tenth is ``"10"``, and so on.

        Parameters
        ----------
        name:
            Display name for the participant.

        Returns
        -------
        Participant
            The newly created participant record.

        Raises
        ------
        SplitTabError
            If the tab is already closed.
        """
        if self._closed:
            raise SplitTabError("Cannot add participant to a closed tab.")
        if self._counter >= 100:
            raise SplitTabError("Tab has reached the maximum of 100 participants.")
        # TODO -> ASk how 0:2d works 
        participant = Participant(id=f"{self._counter:02d}", name=name)
        self._counter += 1
        self._participants.append(participant)
        return participant

    def record_expense(self, description: str, total_cents: int) -> Expense:
        """
        Record a shared expense against all current participants.

        The expense is split among every participant currently on the tab.
        Once recorded, the participant snapshot and total are fixed.

        Parameters
        ----------
        description:
            Human-readable label for the expense.
        total_cents:
            Total amount to split, in integer cents.

        Returns
        -------
        Expense
            The newly recorded expense.

        Raises
        ------
        SplitTabError
            If the tab is already closed.
        """

        if self._closed:
                raise SplitTabError("Cannot record expense to a closed tab.")
        expense = Expense(
            id=self._id_source(),
            description=description,
            total_cents=total_cents,
            participants=tuple(self._participants),
        )
        self._expenses.append(expense)
        return expense

    def close_tab(self) -> None:
        """
        Close the tab.  No further expenses may be recorded after this point.

        Raises
        ------
        SplitTabError
            If the tab is already closed.
        """
        if self._closed:
            raise SplitTabError("Tab is already closed.")
        self._closed = True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def participants(self) -> Tuple[Participant, ...]:
        """Current participants as an immutable snapshot."""
        return tuple(self._participants)

    @property
    def expenses(self) -> Tuple[Expense, ...]:
        """All recorded expenses as an immutable snapshot."""
        return tuple(self._expenses)

    @property
    def is_closed(self) -> bool:
        """True if the tab has been closed."""
        return self._closed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spread_remainder(amounts: List[int], remainder: int) -> None:
    """
    Distribute *remainder* extra cents among the first *remainder* elements
    of *amounts*, one cent each, modifying the list in place.

    The elements beyond index ``remainder - 1`` are unchanged.
    """

    # in future, would have tests
    for i in range(remainder):
        amounts[i] += 1


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def count_payers(expense: Expense) -> int:
    """
    Return the number of payers for *expense*.

    Every participant in the expense receives exactly one share, regardless
    of their display name.

    Parameters
    ----------
    expense:
        A recorded expense as returned by ``SplitTab.record_expense()``.

    Returns
    -------
    int
        Number of participants in the expense.
    """

    #Brendan Notes 
    # Mentions strictly only 2 people can have the name 
    # In the future, identify having some helper that identifies that properly

    # -> coutns unique names (contradicts what we already know about )

    # made this change manually 

    # Erorr handle for zero 
    return len({p.id for p in expense.participants})


# ---------------------------------------------------------------------------
# Split planning
# ---------------------------------------------------------------------------


def plan_splits(expense: Expense) -> SplitPlan:
    """
    Compute the split plan for *expense*.

    Divides ``expense.total_cents`` equally among ``expense.participants``
    using integer (floor) division.  Remainder cents are distributed one at
    a time to participants in their listed order, earliest joiner first.

    Parameters
    ----------
    expense:
        A recorded expense as returned by ``SplitTab.record_expense()``.

    Returns
    -------
    SplitPlan
        Full split breakdown.  ``total_distributed`` equals
        ``expense.total_cents`` exactly.
    """

    # compute integer cents
    num_players = count_payers(expense)
    if num_players <= 0:
        raise SplitTabError("can't have zero payers")

    integer_split = expense.total_cents // num_players
    remainder = expense.total_cents % num_players

    # create list of integer_split to pass into spread_remainder
    amounts = [integer_split] * num_players
    _spread_remainder(amounts, remainder)

    # iterate through split list, creating split objects and tallying total_distributed
    splits = []
    total_distributed = 0
    for participant, amount in zip(expense.participants, amounts):
        splits.append(Split(
            participant_id=participant.id,
            participant_name=participant.name,
            amount_cents=amount,
        ))
        total_distributed += amount

    # add those split objects to SplitPlan in form of TUPLE!
    plan = SplitPlan(splits=tuple(splits), total_distributed=total_distributed)

    # check that total_distributed matches expense.total_cents
    assert plan.total_distributed == expense.total_cents

    return plan
