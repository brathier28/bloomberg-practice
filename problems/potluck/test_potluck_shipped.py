"""
Pre-shipped tests.

These tests were passing when the codebase was handed to you.
They do not constitute a complete test suite.
"""

import pytest

from question import (
    Draw,
    Entry,
    FundraiserError,
    FundraiserPool,
    count_matches,
    plan_payouts,
)


# ---------------------------------------------------------------------------
# Entry registration
# ---------------------------------------------------------------------------


class TestShippedEntryRegistration:
    def test_entering_returns_an_entry_object(self):
        pool = FundraiserPool()
        entry = pool.enter("Alice")
        assert entry is not None
        assert entry.participant == "Alice"

    def test_each_entry_receives_a_unique_id(self):
        pool = FundraiserPool()
        e1 = pool.enter("Alice")
        e2 = pool.enter("Bob")
        assert e1.id != e2.id

    def test_entry_code_is_a_string(self):
        pool = FundraiserPool()
        entry = pool.enter("Alice")
        assert isinstance(entry.code, str)

    def test_pool_records_all_entries_before_draw(self):
        pool = FundraiserPool()
        pool.enter("Alice")
        pool.enter("Bob")
        pool.enter("Carol")
        draw = pool.close_draw()
        assert len(draw.entries) == 3


# ---------------------------------------------------------------------------
# Draw closure
# ---------------------------------------------------------------------------


class TestShippedDrawClosure:
    def test_close_draw_returns_a_draw_object(self):
        pool = FundraiserPool()
        pool.enter("Alice")
        draw = pool.close_draw()
        assert draw is not None

    def test_draw_has_a_string_winning_code(self):
        pool = FundraiserPool()
        draw = pool.close_draw()
        assert isinstance(draw.winning_code, str)

    def test_closing_a_second_time_raises_fundraiser_error(self):
        pool = FundraiserPool()
        pool.close_draw()
        with pytest.raises(FundraiserError):
            pool.close_draw()

    def test_pot_for_four_entries_is_sponsor_seed_plus_twenty_dollars(self):
        pool = FundraiserPool()
        for name in ["A", "B", "C", "D"]:
            pool.enter(name)
        draw = pool.close_draw()
        assert draw.pot_cents == 1_002_000  # $10,000 + 4 × $5


# ---------------------------------------------------------------------------
# Match counting (cases chosen to avoid positional edge cases)
# ---------------------------------------------------------------------------


class TestShippedMatchCounting:
    def test_identical_codes_with_all_unique_digits_score_five(self):
        assert count_matches("12345", "12345") == 5

    def test_completely_disjoint_codes_score_zero(self):
        assert count_matches("12345", "67890") == 0

    def test_first_two_positions_matching_scores_two(self):
        assert count_matches("12345", "12000") == 2

    def test_first_three_positions_matching_scores_three(self):
        assert count_matches("12345", "12300") == 3

    def test_first_four_positions_matching_scores_four(self):
        assert count_matches("12345", "12346") == 4


# ---------------------------------------------------------------------------
# Payout plan (single-winner tiers to avoid splitting)
# ---------------------------------------------------------------------------


class TestShippedPayoutPlan:
    def test_single_four_match_entry_receives_forty_percent_of_pot(self):
        entry = Entry(id="e1", participant="Alice", code="12345")
        draw = Draw(winning_code="12346", pot_cents=1_002_000, entries=(entry,))
        plan = plan_payouts(draw)
        assert plan.awarded_cents == 400_800  # 40% of $10,020

    def test_zero_matching_entries_produce_full_rollover(self):
        entry = Entry(id="e1", participant="Alice", code="12345")
        draw = Draw(winning_code="67890", pot_cents=1_000_000, entries=(entry,))
        plan = plan_payouts(draw)
        assert plan.awarded_cents == 0
        assert plan.rollover_cents == 1_000_000

    def test_awarded_cents_plus_rollover_cents_always_equal_pot(self):
        entry = Entry(id="e1", participant="Alice", code="12345")
        draw = Draw(winning_code="12345", pot_cents=1_000_000, entries=(entry,))
        plan = plan_payouts(draw)
        assert plan.awarded_cents + plan.rollover_cents == 1_000_000

    def test_entry_with_no_positional_matches_receives_no_payout(self):
        entry = Entry(id="e1", participant="Alice", code="12345")
        draw = Draw(winning_code="61789", pot_cents=1_000_000, entries=(entry,))
        plan = plan_payouts(draw)
        assert plan.awarded_cents == 0
