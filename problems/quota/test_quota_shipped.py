"""
Pre-shipped tests.

These tests were passing when the codebase was handed to you.
They do not constitute a complete test suite.
"""

import pytest

from question import (
    Batch,
    Bill,
    ClientLog,
    Decision,
    LineItem,
    RateLimitError,
    RateLimiter,
    compute_bill,
    tier_for,
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestShippedRegistration:
    def test_register_a_new_client_does_not_raise(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=5)

    def test_registering_the_same_client_twice_raises(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=5)
        with pytest.raises(RateLimitError):
            limiter.register("alice", quota=10)

    def test_requesting_for_an_unregistered_client_raises(self):
        limiter = RateLimiter()
        with pytest.raises(RateLimitError):
            limiter.request("ghost", timestamp_ms=1_000)


# ---------------------------------------------------------------------------
# Suspension
# ---------------------------------------------------------------------------


class TestShippedSuspension:
    def test_suspending_unregistered_client_raises(self):
        limiter = RateLimiter()
        with pytest.raises(RateLimitError):
            limiter.suspend("ghost")

    def test_suspended_client_request_is_rejected_with_suspended_reason(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=5)
        limiter.suspend("alice")
        decision = limiter.request("alice", timestamp_ms=1_000)
        assert decision.allowed is False
        assert decision.reason == "SUSPENDED"


# ---------------------------------------------------------------------------
# Quota and window
# ---------------------------------------------------------------------------


class TestShippedQuotaAndWindow:
    def test_a_single_request_within_quota_is_allowed(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=3)
        decision = limiter.request("alice", timestamp_ms=10)
        assert decision.allowed is True
        assert decision.reason is None

    def test_three_requests_fit_within_quota_of_three(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=3)
        for ts in (10, 20, 30):
            d = limiter.request("alice", timestamp_ms=ts)
            assert d.allowed is True

    def test_fourth_request_within_short_span_exceeds_quota_of_three(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=3)
        for ts in (10, 20, 30):
            limiter.request("alice", timestamp_ms=ts)
        decision = limiter.request("alice", timestamp_ms=40)
        assert decision.allowed is False
        assert decision.reason == "QUOTA_EXCEEDED"


# ---------------------------------------------------------------------------
# Batch close
# ---------------------------------------------------------------------------


class TestShippedBatchClose:
    def test_close_batch_returns_a_batch_object(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=5)
        batch = limiter.close_batch()
        assert isinstance(batch, Batch)

    def test_closing_a_second_time_raises(self):
        limiter = RateLimiter()
        limiter.close_batch()
        with pytest.raises(RateLimitError):
            limiter.close_batch()

    def test_batch_contains_one_client_log_per_registered_client(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=5)
        limiter.register("bob", quota=10)
        limiter.register("carol", quota=100)
        batch = limiter.close_batch()
        assert len(batch.clients) == 3

    def test_closed_batch_client_log_preserves_quota(self):
        limiter = RateLimiter()
        limiter.register("alice", quota=5)
        batch = limiter.close_batch()
        assert batch.clients[0].quota == 5


# ---------------------------------------------------------------------------
# Tier lookup (chosen to avoid tier boundary edges)
# ---------------------------------------------------------------------------


class TestShippedTierLookup:
    def test_small_count_is_starter(self):
        assert tier_for(0) == "starter"
        assert tier_for(50) == "starter"

    def test_moderate_count_is_standard(self):
        assert tier_for(250) == "standard"


# ---------------------------------------------------------------------------
# Bill computation (will fail with NotImplementedError until implemented)
# ---------------------------------------------------------------------------


class TestShippedComputeBill:
    def test_bill_for_an_empty_batch_has_zero_total_and_no_line_items(self):
        batch = Batch(clients=())
        bill = compute_bill(batch)
        assert bill.total_cents == 0
        assert bill.line_items == ()

    def test_single_allowed_request_costs_starter_rate(self):
        cl = ClientLog(
            client_id="alice",
            quota=5,
            suspended=False,
            allowed_timestamps_ms=(10,),
            rejected_count=0,
        )
        batch = Batch(clients=(cl,))
        bill = compute_bill(batch)
        assert bill.total_cents == 15  # 15 cents per starter-tier allowed request

    def test_suspended_client_is_charged_flat_suspension_fee(self):
        cl = ClientLog(
            client_id="alice",
            quota=5,
            suspended=True,
            allowed_timestamps_ms=(),
            rejected_count=0,
        )
        batch = Batch(clients=(cl,))
        bill = compute_bill(batch)
        assert bill.total_cents == 1_000

    def test_bill_total_equals_sum_of_line_item_costs(self):
        cl = ClientLog(
            client_id="alice",
            quota=5,
            suspended=False,
            allowed_timestamps_ms=(10, 20, 30),
            rejected_count=1,
        )
        batch = Batch(clients=(cl,))
        bill = compute_bill(batch)
        assert bill.total_cents == sum(li.cost_cents for li in bill.line_items)
