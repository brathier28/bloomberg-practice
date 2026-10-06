"""
sample_run.py — happy-path demonstration of Pot Luck.

Run with:  python3 sample_run.py
"""

import random

from question import FundraiserPool, count_matches, plan_payouts

random.seed(7)

pool = FundraiserPool()

participants = [
    "Alice",
    "Bob",
    "Carol",
    "Dave",
    "Eve",
    "Frank",
]

print("=== Registering entries ===")
entries = []
for name in participants:
    entry = pool.enter(name)
    entries.append(entry)
    print(f"  {entry.participant:8s}  code={entry.code}")

print()
draw = pool.close_draw()
print(f"=== Draw closed ===")
print(f"  Winning code : {draw.winning_code}")
print(f"  Pot          : ${draw.pot_cents / 100:,.2f}  ({draw.pot_cents} cents)")
print(f"  Entries      : {len(draw.entries)}")

print()
print("=== Match results ===")
for e in draw.entries:
    m = count_matches(e.code, draw.winning_code)
    bar = "#" * m + "-" * (5 - m)
    print(f"  {e.participant:8s}  {e.code} vs {draw.winning_code}  [{bar}]  {m} match(es)")

print()
plan = plan_payouts(draw)
print("=== Payout plan ===")
if plan.payouts:
    for p in plan.payouts:
        print(f"  {p.participant:8s}  {p.match_count} match(es)  ${p.amount_cents / 100:,.2f}")
else:
    print("  (no winners this draw)")

print()
print(f"  Awarded  : ${plan.awarded_cents / 100:,.2f}")
print(f"  Rollover : ${plan.rollover_cents / 100:,.2f}")
print(f"  Total    : ${(plan.awarded_cents + plan.rollover_cents) / 100:,.2f}")
