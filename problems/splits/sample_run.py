"""
sample_run.py — happy-path demonstration of Tab Split.

Run with:  python3 sample_run.py
"""

from question import SplitTab, count_payers, plan_splits

tab = SplitTab()

participants = ["Alice", "Bob", "Carol", "Dave", "Eve"]

print("=== Adding participants ===")
for name in participants:
    tab.add_participant(name)
    print(f"  {name}")

print()
print("=== Recording expenses ===")

e1 = tab.record_expense("Team lunch", 5000)
e2 = tab.record_expense("Taxi ride", 2500)

for e in [e1, e2]:
    print(f"  {e.description}: {e.total_cents} cents, {count_payers(e)} payers")

print()
print("=== Split plan for Team lunch ===")
plan = plan_splits(e1)
for s in plan.splits:
    print(f"  {s.participant_name:8s}  {s.amount_cents} cents")
print(f"  Total distributed: {plan.total_distributed} cents")

print()
tab.close_tab()
print("Tab closed.")
