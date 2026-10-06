"""
Shared pytest fixtures for the Pot Luck test suite.

Import these in any test file by declaring them as parameters — pytest
injects them automatically.

    def test_something(make_pool, make_draw):
        pool = make_pool(lambda: 0.5)
        draw = make_draw("12345", 1_002_000, [("Alice", "12345")])
"""

import pytest

from question import Draw, Entry, FundraiserPool


@pytest.fixture
def fresh_pool():
    """A FundraiserPool with the default (unseeded) random source."""
    return FundraiserPool()


@pytest.fixture
def make_pool():
    """
    Factory that creates a FundraiserPool with a controlled random source.

    Usage::

        def test_example(make_pool):
            pool = make_pool(lambda: 0.5)
            entry = pool.enter("Alice")
    """
    def _factory(random_source=None):
        return FundraiserPool(random_source=random_source)

    return _factory


@pytest.fixture
def make_draw():
    """
    Factory that builds a Draw directly from known codes, bypassing FundraiserPool.

    Useful for plan_payouts tests where you need exact codes.

    Parameters
    ----------
    winning_code : str
        The draw's winning code.
    pot_cents : int
        Total pot in cents.
    entries : list of (participant_name, code) tuples
        Entries to include in the draw snapshot.

    Usage::

        def test_payout(make_draw):
            draw = make_draw(
                "12345",
                1_002_000,
                [("Alice", "12345"), ("Bob", "67890")],
            )
            plan = plan_payouts(draw)
    """
    def _factory(winning_code: str, pot_cents: int, entries):
        entry_objects = tuple(
            Entry(id=str(i), participant=name, code=code)
            for i, (name, code) in enumerate(entries)
        )
        return Draw(
            winning_code=winning_code,
            pot_cents=pot_cents,
            entries=entry_objects,
        )

    return _factory
