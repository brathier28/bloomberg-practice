"""
Pre-shipped tests.

These tests were passing when the codebase was handed to you.
They do not constitute a complete test suite.
"""

import pytest

from question import (
    Expense,
    Participant,
    SplitTab,
    SplitTabError,
    count_payers,
    plan_splits,
)


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


class TestShippedParticipants:
    def test_added_participant_has_the_given_name(self):
        tab = SplitTab()
        p = tab.add_participant("Alice")
        assert p.name == "Alice"

    def test_each_participant_receives_a_unique_id(self):
        tab = SplitTab()
        p1 = tab.add_participant("Alice")
        p2 = tab.add_participant("Bob")
        assert p1.id != p2.id

    def test_participants_property_returns_all_added(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        tab.add_participant("Carol")
        assert len(tab.participants) == 3


# ---------------------------------------------------------------------------
# Expense recording
# ---------------------------------------------------------------------------


class TestShippedExpenseRecording:
    def test_recorded_expense_carries_the_given_description(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        expense = tab.record_expense("Lunch", 1200)
        assert expense.description == "Lunch"

    def test_recorded_expense_carries_the_given_total(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        expense = tab.record_expense("Lunch", 1200)
        assert expense.total_cents == 1200

    def test_expense_includes_all_participants_at_record_time(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        expense = tab.record_expense("Dinner", 3000)
        assert len(expense.participants) == 2

    def test_expenses_property_returns_all_recorded(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.record_expense("Lunch", 1200)
        tab.record_expense("Dinner", 3000)
        assert len(tab.expenses) == 2

    def test_expense_participant_snapshot_is_fixed(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        expense = tab.record_expense("Dinner", 1000)

        tab.add_participant("Bob")   # joins after expense was recorded

        assert len(expense.participants) == 1
        assert expense.participants[0].name == "Alice"


# ---------------------------------------------------------------------------
# Tab lifecycle
# ---------------------------------------------------------------------------


class TestShippedTabLifecycle:
    def test_tab_starts_open(self):
        tab = SplitTab()
        assert not tab.is_closed

    def test_close_tab_marks_the_tab_closed(self):
        tab = SplitTab()
        tab.close_tab()
        assert tab.is_closed

    def test_closing_an_already_closed_tab_raises_error(self):
        tab = SplitTab()
        tab.close_tab()
        with pytest.raises(SplitTabError):
            tab.close_tab()


# ---------------------------------------------------------------------------
# count_payers  (inputs chosen to avoid duplicate-name edge case)
# ---------------------------------------------------------------------------


class TestShippedCountPayers:
    def test_count_payers_returns_participant_count_for_unique_names(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        tab.add_participant("Carol")
        expense = tab.record_expense("Dinner", 3000)
        assert count_payers(expense) == 3

    def test_count_payers_for_a_single_participant_is_one(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        expense = tab.record_expense("Coffee", 500)
        assert count_payers(expense) == 1


# ---------------------------------------------------------------------------
# plan_splits  (all fail with NotImplementedError — that is expected)
# ---------------------------------------------------------------------------


class TestShippedPlanSplits:
    def test_total_distributed_equals_expense_total_for_even_split(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        tab.add_participant("Carol")
        expense = tab.record_expense("Dinner", 300)
        plan = plan_splits(expense)
        assert plan.total_distributed == 300

    def test_split_count_equals_participant_count(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        tab.add_participant("Carol")
        expense = tab.record_expense("Pizza", 600)
        plan = plan_splits(expense)
        assert len(plan.splits) == 3

    def test_each_participant_appears_in_the_split_plan(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        expense = tab.record_expense("Snacks", 400)
        plan = plan_splits(expense)
        names = {s.participant_name for s in plan.splits}
        assert names == {"Alice", "Bob"}

    def test_every_split_amount_is_a_positive_integer(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        expense = tab.record_expense("Taxi", 200)
        plan = plan_splits(expense)
        assert all(isinstance(s.amount_cents, int) and s.amount_cents > 0
                   for s in plan.splits)
