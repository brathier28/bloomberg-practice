"""
sample_run.py — happy-path demonstration of Quota.

Run with:  python3 sample_run.py
"""

from question import RateLimiter, compute_bill

limiter = RateLimiter(window_seconds=60)

print("=== Registering clients ===")
limiter.register("alice", quota=100)
limiter.register("bob", quota=50)
limiter.register("carol", quota=10)
limiter.suspend("bob")
print("  alice  quota=100  active")
print("  bob    quota=50   suspended")
print("  carol  quota=10   active")

clients = ["alice", "bob", "carol"]
timestamps = [1_000, 1_010, 1_020, 1_030, 1_040]

print()
print("=== Decisions ===")
for cid in clients:
    for ts in timestamps:
        decision = limiter.request(cid, timestamp_ms=ts)
        verdict = "ALLOW" if decision.allowed else f"REJECT ({decision.reason})"
        print(f"  {cid:6s}  t={ts}  -> {verdict}")

print()
batch = limiter.close_batch()
print("=== Batch closed ===")
for cl in batch.clients:
    print(
        f"  {cl.client_id:6s}  quota={cl.quota:<4}  "
        f"suspended={cl.suspended}  "
        f"allowed={len(cl.allowed_timestamps_ms)}  "
        f"rejected={cl.rejected_count}"
    )

print()
print("=== Bill ===")
try:
    bill = compute_bill(batch)
    for li in bill.line_items:
        print(
            f"  {li.client_id:6s}  tier={li.tier:<10}  "
            f"allowed={li.allowed_count}  rejected={li.rejected_count}  "
            f"cost=${li.cost_cents / 100:,.2f}"
        )
    print(f"  Total: ${bill.total_cents / 100:,.2f}")
except NotImplementedError as e:
    print(f"  compute_bill not implemented yet: {e}")
