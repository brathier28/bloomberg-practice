"""
Quota — API Rate Limiter and Billing

Backend for a per-client API gateway rate limiter.  Clients register
with a quota (requests per sliding window), send requests, and are
either allowed or rejected.  At the end of a billing cycle the batch
is closed and the system produces a tiered bill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WINDOW_SECONDS: int = 60
SUSPENSION_FEE_CENTS: int = 1_000       # flat $10 fee for suspended clients
REJECTION_PENALTY_CENTS: int = 2        # per rejected request

TIER_RATES_CENTS: Dict[str, int] = {
    "starter": 15,
    "standard": 10,
    "enterprise": 5,
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RateLimitError(Exception):
    """Raised for invalid rate-limiter operations."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    """The outcome of a single rate-limit decision."""

    allowed: bool
    reason: Optional[str]


@dataclass(frozen=True)
class ClientLog:
    """A snapshot of one client's state at batch close."""

    client_id: str
    quota: int
    suspended: bool
    allowed_timestamps_ms: Tuple[int, ...]
    rejected_count: int


@dataclass(frozen=True)
class Batch:
    """An immutable snapshot of a closed billing cycle."""

    clients: Tuple[ClientLog, ...]


@dataclass(frozen=True)
class LineItem:
    """A single line in the computed bill."""

    client_id: str
    tier: str
    allowed_count: int
    rejected_count: int
    cost_cents: int


@dataclass(frozen=True)
class Bill:
    """The complete result of running compute_bill on a Batch."""

    line_items: Tuple[LineItem, ...]
    total_cents: int


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Per-client sliding-window rate limiter.

    Usage::

        limiter = RateLimiter(window_seconds=60)
        limiter.register("alice", quota=5)
        decision = limiter.request("alice", timestamp_ms=1_000)
        batch = limiter.close_batch()
    """

    def __init__(self, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> None:
        """
        Parameters
        ----------
        window_seconds:
            Length of the sliding window, in seconds.  Comparisons use
            integer milliseconds internally.
        """
        self._window_ms: int = window_seconds
        self._clients: Dict[str, Dict] = {}
        self._batch: Optional[Batch] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _in_window(self, timestamps_ms: List[int], now_ms: int) -> int:
        """Return the count of ``timestamps_ms`` falling in ``(now_ms - W, now_ms]``."""
        cutoff = now_ms - self._window_ms
        return len({t for t in timestamps_ms if t > cutoff})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, client_id: str, quota: int) -> None:
        """
        Register a new client with the given per-window quota.

        Raises
        ------
        RateLimitError
            If the client is already registered, or the billing cycle is closed.
        """
        if self._batch is not None:
            raise RateLimitError("Billing cycle is closed.")
        if client_id in self._clients:
            raise RateLimitError(f"Client {client_id!r} already registered.")
        self._clients[client_id] = {
            "quota": quota,
            "suspended": False,
            "allowed_ts": [],
            "rejected_count": 0,
        }

    def suspend(self, client_id: str) -> None:
        """
        Suspend a registered client.  Suspended clients have all requests rejected.

        Raises
        ------
        RateLimitError
            If the client is unknown, or the billing cycle is closed.
        """
        if self._batch is not None:
            raise RateLimitError("Billing cycle is closed.")
        if client_id not in self._clients:
            raise RateLimitError(f"Unknown client {client_id!r}.")
        self._clients[client_id]["suspended"] = True

    def request(self, client_id: str, timestamp_ms: int) -> Decision:
        """
        Decide whether an incoming request from *client_id* at *timestamp_ms* is allowed.

        Suspended clients are always rejected with reason ``"SUSPENDED"``.
        Otherwise, if the client's prior allowed requests in the current window
        already fill the quota, the request is rejected with reason
        ``"QUOTA_EXCEEDED"``.  Allowed requests are recorded in the client's log;
        rejected requests are counted but not logged.

        Raises
        ------
        RateLimitError
            If the client is unknown, or the billing cycle is closed.
        """
        if client_id not in self._clients:
            raise RateLimitError(f"Unknown client {client_id!r}.")
        state = self._clients[client_id]
        if state["suspended"]:
            state["rejected_count"] += 1
            return Decision(allowed=False, reason="SUSPENDED")
        count = self._in_window(state["allowed_ts"], timestamp_ms)
        if count >= state["quota"]:
            state["rejected_count"] += 1
            return Decision(allowed=False, reason="QUOTA_EXCEEDED")
        state["allowed_ts"].append(timestamp_ms)
        return Decision(allowed=True, reason=None)

    def close_batch(self) -> Batch:
        """
        Close the current billing cycle and return a frozen snapshot of client state.

        Returns
        -------
        Batch
            A record containing a per-client log for every registered client.

        Raises
        ------
        RateLimitError
            If the billing cycle has already been closed.
        """
        if self._batch is not None:
            raise RateLimitError("Billing cycle is already closed.")
        logs = tuple(
            ClientLog(
                client_id=cid,
                quota=s["quota"],
                suspended=s["suspended"],
                allowed_timestamps_ms=s["allowed_ts"],
                rejected_count=s["rejected_count"],
            )
            for cid, s in self._clients.items()
        )
        self._batch = Batch(clients=logs)
        return self._batch

    @property
    def batch(self) -> Optional[Batch]:
        """The closed Batch, or None if the cycle is still open."""
        return self._batch


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def tier_for(allowed_count: int) -> str:
    """
    Return the pricing tier name for a client with the given allowed-request count.

    Tiers:

    - ``"starter"``: fewer than 100 allowed requests.
    - ``"standard"``: at least 100 but fewer than 1000 allowed requests.
    - ``"enterprise"``: 1000 or more allowed requests.
    """
    if allowed_count < 100:
        return "starter"
    if allowed_count <= 1000:
        return "standard"
    return "enterprise"


# ---------------------------------------------------------------------------
# Bill computation
# ---------------------------------------------------------------------------


def compute_bill(batch: Batch) -> Bill:
    """
    Compute the bill for a closed billing cycle.

    For each client in *batch*:

    - A **suspended** client is charged a flat ``SUSPENSION_FEE_CENTS`` and
      their line-item tier is reported as ``"suspended"``.
    - A **non-suspended** client is charged ``rate * allowed_count +
      REJECTION_PENALTY_CENTS * rejected_count``, where ``rate`` comes from
      ``TIER_RATES_CENTS`` based on ``tier_for(allowed_count)``.

    ``Bill.total_cents`` is the sum of all line-item costs.

    Parameters
    ----------
    batch:
        A closed Batch as returned by ``RateLimiter.close_batch()``.

    Returns
    -------
    Bill
        A record containing per-client line items and the overall total.
    """

    raise NotImplementedError("compute_bill is not implemented.")
