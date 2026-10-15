"""
Your test file.  Add tests here.
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

# Add your tests here.


class TestAddParticipant:
    def test_id_is_length_two_string(self):
        tab = SplitTab()
        p = tab.add_participant("Alice")
        assert isinstance(p.id, str)
        assert len(p.id) == 2

    def test_ids_zero_through_ninetynine_are_valid(self):
        tab = SplitTab()
        participants = [tab.add_participant("Person") for _ in range(100)]
        assert participants[0].id == "00"
        assert participants[9].id == "09"
        assert participants[10].id == "10"
        assert participants[99].id == "99"

    def test_101st_participant_raises(self):
        tab = SplitTab()
        for _ in range(100):
            tab.add_participant("Person")
        with pytest.raises(SplitTabError):
            tab.add_participant("One Too Many")


class TestRecordExpense:
    def test_record_expense_on_closed_tab_raises(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.close_tab()
        with pytest.raises(SplitTabError):
            tab.record_expense("Dinner", 1000)


class TestPlanSplits:
    def test_even_split_per_person_amount(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        tab.add_participant("Carol")
        expense = tab.record_expense("Dinner", 300)
        plan = plan_splits(expense)
        assert all(s.amount_cents == 100 for s in plan.splits)

    def test_remainder_goes_to_earliest_joiner_first(self):
        tab = SplitTab()
        tab.add_participant("Zoe")
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        expense = tab.record_expense("Dinner", 1001)
        plan = plan_splits(expense)
        amounts = {s.participant_name: s.amount_cents for s in plan.splits}
        assert amounts["Zoe"] == 334
        assert amounts["Alice"] == 334
        assert amounts["Bob"] == 333

    def test_same_name_participants_each_get_own_share(self):
        tab = SplitTab()
        tab.add_participant("Alex")
        tab.add_participant("Alex")
        expense = tab.record_expense("Coffee", 101)
        plan = plan_splits(expense)
        assert len(plan.splits) == 2
        assert sum(s.amount_cents for s in plan.splits) == 101

    def test_total_distributed_equals_total_cents_with_remainder(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        tab.add_participant("Bob")
        expense = tab.record_expense("Taxi", 201)
        plan = plan_splits(expense)
        assert plan.total_distributed == expense.total_cents

    def test_split_plan_and_splits_are_frozen(self):
        tab = SplitTab()
        tab.add_participant("Alice")
        expense = tab.record_expense("Lunch", 500)
        plan = plan_splits(expense)
        with pytest.raises(Exception):
            plan.total_distributed = 999
        with pytest.raises(Exception):
            plan.splits[0].amount_cents = 999
