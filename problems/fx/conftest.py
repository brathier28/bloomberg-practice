"""Shared pytest fixtures for the FX desk test suite."""
import pytest

from question import ConversionRequest, Desk, Session


@pytest.fixture
def desk():
    """A fresh Desk ready to accept submissions.

    Example::

        def test_something(desk):
            req = desk.submit("Alice", "EURUSD", 500_000)
    """
    return Desk(seed_cents=10_000_000, rate_source=lambda pair: 10_000)


@pytest.fixture
def make_desk():
    """Factory for Desk instances with a custom rate source or seed.

    Example::

        def test_something(make_desk):
            desk = make_desk(rate_source=lambda pair: 10_842)
            req = desk.submit("Alice", "EURUSD", 500_000)
    """

    def _factory(seed_cents: int = 10_000_000, rate_source=None):
        if rate_source is None:
            rate_source = lambda pair: 10_000
        return Desk(seed_cents=seed_cents, rate_source=rate_source)

    return _factory


@pytest.fixture
def make_session():
    """Build a Session directly from known values, bypassing Desk.

    Useful for plan_settlement tests where you need exact requests and rates.

    Example::

        def test_something(make_session):
            req = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
            session = make_session(requests=(req,), rates={"EURUSD": 10_842})
    """

    def _factory(requests=(), seed_cents: int = 10_000_000, rates=None):
        if rates is None:
            rates = {}
        return Session(requests=requests, seed_cents=seed_cents, rates=rates)

    return _factory
