"""
sample_run.py — happy-path demonstration of Trade Settlement Netting.

Run with:  python3 sample_run.py
"""

from datetime import date

from question import TradeBook, net_obligations

_counter = 0


def _next_id():
    global _counter
    _counter += 1
    return f"T{_counter:04d}"


cutoff = date(2026, 10, 20)
book = TradeBook(cutoff_date=cutoff, id_source=_next_id)

_trades = [
    ("ALPHA", "USD", "buy",  1_200_000, date(2026, 10, 17)),
    ("ALPHA", "USD", "buy",    800_000, date(2026, 10, 17)),
    ("ALPHA", "EUR", "buy",    750_000, date(2026, 10, 18)),
    ("BRAVO", "USD", "buy",    300_000, date(2026, 10, 19)),
    ("BRAVO", "GBP", "buy",    500_000, date(2026, 10, 22)),
]

print("=== Adding trades ===")
for cp, ccy, direction, notional, settle in _trades:
    t = book.add_trade(cp, ccy, direction, notional, settle)
    scope = "in scope" if settle <= cutoff else "out of scope"
    print(f"  {t.id}  {cp:6s} {ccy} {direction:4s}  {notional:>12,}  {settle}  ({scope})")

print()
book.lock()
print(f"Book locked. {len(book.locked_trades)} trades recorded.")

print()
try:
    run = net_obligations(book)
    print("=== Netting run ===")
    for ob in run.obligations:
        print(
            f"  {ob.direction:8s}  {ob.amount_cents:>12,} {ob.currency}"
            f"  from/to {ob.counterparty}  settle {ob.settlement_date}"
        )
    print()
    print(f"  Total receive : {run.total_receive_cents:>12,}")
    print(f"  Total pay     : {run.total_pay_cents:>12,}")
except NotImplementedError:
    print("net_obligations is not yet implemented.")
