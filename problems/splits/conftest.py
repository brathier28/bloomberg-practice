"""
Shared pytest fixtures for the Tab Split test suite.

Import these in any test file by declaring them as parameters — pytest
injects them automatically.

    def test_something(make_tab, make_expense):
        tab = make_tab()
        p = tab.add_participant("Alice")
"""

import pytest

from question import Expense, Participant, SplitTab


@pytest.fixture
def fresh_tab():
    """A SplitTab with no participants and a fresh state."""
    return SplitTab()


@pytest.fixture
def make_tab():
    """
    Factory that creates a SplitTab with a controlled ID source.

    Usage::

        def test_example(make_tab):
            tab = make_tab()
            p = tab.add_participant("Alice")
    """
    def _factory(id_source=None):
        return SplitTab(id_source=id_source)

    return _factory


@pytest.fixture
def make_expense():
    """
    Factory that builds an Expense directly from known values, bypassing SplitTab.

    Useful for plan_splits and count_payers tests where you need exact
    participant order and IDs.

    Parameters
    ----------
    total_cents : int
        Total expense amount in cents.
    participants : list of (name, id) tuples
        Participants to include, in order.  Each tuple is (name, id).
    description : str, optional
        Expense description.

    Usage::

        def test_example(make_expense):
            expense = make_expense(
                total_cents=900,
                participants=[("Alice", "p0"), ("Bob", "p1"), ("Carol", "p2")],
            )
            plan = plan_splits(expense)
    """
    def _factory(total_cents, participants, description="Test"):
        p_objects = tuple(
            Participant(id=pid, name=name)
            for name, pid in participants
        )
        return Expense(
            id="test-expense",
            description=description,
            total_cents=total_cents,
            participants=p_objects,
        )

    return _factory
