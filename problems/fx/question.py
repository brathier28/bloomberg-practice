"""Bloomberg FX Desk — Daily Settlement."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


class DeskError(Exception):
    """Raised when a desk operation is not permitted."""


SMALL_THRESHOLD = 1_000_000    # source cents; notional below this → Tier 1
LARGE_THRESHOLD = 10_000_000   # source cents; notional at or above this → Tier 3


@dataclass(frozen=True)
class ConversionRequest:
    """A single FX conversion request."""

    id: str
    participant: str
    pair: str            # e.g. "EURUSD"
    notional_cents: int  # amount in source-currency cents

@dataclass(frozen=True)
class Session:
    """Locked snapshot of a desk's state at close."""

    requests: Tuple[ConversionRequest, ...]
    seed_cents: int
    rates: Dict[str, int]  # pair → mid-rate bps, locked at close


@dataclass(frozen=True)
class Settlement:
    """One settled conversion record."""

    request_id: str
    participant: str
    pair: str
    notional_cents: int
    spread_bps: int
    usd_cents: int


@dataclass(frozen=True)
class SettlementReport:
    """Final report for a closed session."""

    settlements: Tuple[Settlement, ...]
    total_usd_cents: int
    rollover_cents: int


class Desk:
    """Accepts conversion requests while open; produces a Session on close."""

    def __init__(self, seed_cents: int, rate_source: Callable[[str], int]) -> None:
        self._seed_cents = seed_cents
        self._rate_source = rate_source
        self._requests: List[ConversionRequest] = []
        self._session: Optional[Session] = None

    @property
    def is_open(self) -> bool:
        return self._session is None

    def submit(
        self, participant: str, pair: str, notional_cents: int
    ) -> ConversionRequest:
        """Accept a new conversion request.

        Raises DeskError if the desk is already closed.
        Returns the created ConversionRequest.
        """
        req = ConversionRequest(
            id=str(uuid.uuid4()),
            participant=participant,
            pair=pair,
            notional_cents=notional_cents,
        )
        self._requests.append(req)
        return req

    def close(self) -> Session:
        """Lock the desk and return a frozen snapshot of the session.

        Looks up mid-rates for all submitted pairs at close time.
        No further submissions are accepted after close.
        """
        pairs = {req.pair for req in self._requests}
        rates = {pair: self._rate_source(pair) for pair in pairs}
        self._session = Session(
            requests=self._requests,
            seed_cents=self._seed_cents,
            rates=rates,
        )
        return self._session


def _get_spread(notional_cents: int) -> int:
    """Return spread in bps for the given notional.

    Tier 1 (notional < 1,000,000 cents): 50 bps.
    Tier 2 (1,000,000 <= notional < 10,000,000 cents): 20 bps.
    Tier 3 (notional >= 10,000,000 cents): 5 bps.
    """
    if notional_cents < SMALL_THRESHOLD:
        return 50
    if notional_cents <= LARGE_THRESHOLD:
        return 20
    return 5


def _compute_usd_cost(
    notional_cents: int, mid_rate_bps: int, spread_bps: int
) -> int:
    """Return USD cost in cents: floor(notional × (mid_rate + spread) / 10,000)."""
    all_in_rate = mid_rate_bps + spread_bps
    return notional_cents * all_in_rate / 10_000


def _settle_requests(
    requests: Tuple[ConversionRequest, ...],
    rates: Dict[str, int],
) -> List[Settlement]:
    """Return one Settlement per request.

    Each request is processed independently — two requests with the same
    participant and pair are both settled.
    """
    seen: Dict = {}
    for req in requests:
        seen[(req.participant, req.pair)] = req

    result = []
    for req in seen.values():
        mid_rate = rates[req.pair]
        spread = _get_spread(req.notional_cents)
        usd = _compute_usd_cost(req.notional_cents, mid_rate, spread)
        result.append(
            Settlement(
                request_id=req.id,
                participant=req.participant,
                pair=req.pair,
                notional_cents=req.notional_cents,
                spread_bps=spread,
                usd_cents=usd,
            )
        )
    return result


def plan_settlement(session: Session) -> SettlementReport:
    """Compute the settlement report for a closed session.

    Returns one Settlement per request, the total USD cost in cents, and
    rollover (seed minus total; negative when costs exceed seed).
    """
    raise NotImplementedError("plan_settlement is not implemented.")
