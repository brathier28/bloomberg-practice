"""
Shared pytest fixtures for the Quota test suite.

Import these in any test file by declaring them as parameters — pytest
injects them automatically.

    def test_something(make_limiter, make_batch):
        limiter = make_limiter(window_seconds=60)
        batch = make_batch([
            {"client_id": "alice", "quota": 5, "allowed_ts": (10, 20)},
        ])
"""

import pytest

from question import Batch, ClientLog, RateLimiter


@pytest.fixture
def fresh_limiter():
    """A RateLimiter with the default window."""
    return RateLimiter()


@pytest.fixture
def make_limiter():
    """
    Factory that creates a RateLimiter with a configurable window.

    Usage::

        def test_example(make_limiter):
            limiter = make_limiter(window_seconds=60)
            limiter.register("alice", quota=5)
    """
    def _factory(window_seconds=60):
        return RateLimiter(window_seconds=window_seconds)

    return _factory


@pytest.fixture
def make_batch():
    """
    Factory that builds a Batch directly from client descriptions, bypassing RateLimiter.

    Useful for ``compute_bill`` tests where you need exact client state.

    Parameters
    ----------
    clients : list of dicts
        Each dict may contain:
          - ``client_id`` (str, required)
          - ``quota`` (int, default 10)
          - ``suspended`` (bool, default False)
          - ``allowed_ts`` (tuple of int, default ())
          - ``rejected_count`` (int, default 0)

    Usage::

        def test_bill(make_batch):
            batch = make_batch([
                {"client_id": "alice", "allowed_ts": (10, 20, 30)},
                {"client_id": "bob", "suspended": True},
            ])
    """
    def _factory(clients):
        logs = tuple(
            ClientLog(
                client_id=c["client_id"],
                quota=c.get("quota", 10),
                suspended=c.get("suspended", False),
                allowed_timestamps_ms=tuple(c.get("allowed_ts", ())),
                rejected_count=c.get("rejected_count", 0),
            )
            for c in clients
        )
        return Batch(clients=logs)

    return _factory
