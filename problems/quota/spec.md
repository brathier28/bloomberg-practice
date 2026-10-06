# Quota — API Rate Limiter and Billing

## Overview

You are implementing the backend for an API gateway product called **Quota**. The system registers API clients, decides whether each incoming request is allowed under a sliding-window quota, snapshots the resulting activity at the end of a billing cycle, and produces a tiered bill.

---

## Clients

- Each client registers with a `client_id` (string) and a `quota` (positive integer: maximum allowed requests per sliding window).
- Registering the same `client_id` twice raises `RateLimitError`.
- A registered client may be **suspended**. While suspended, every request is rejected regardless of quota or window.
- Suspending an unregistered client raises `RateLimitError`. Suspending an already-suspended client is a no-op.

---

## Requests

- `request(client_id, timestamp_ms)` is called for every incoming API request.
- Timestamps are **integer milliseconds** since epoch and are **monotonically non-decreasing** per client.
- Requests for an unregistered client raise `RateLimitError`.

### Decision rule

For a request at time `T` from a client with quota `Q`:

1. If the client is **suspended**, the request is rejected with reason `"SUSPENDED"`.
2. Otherwise, count the client's **prior allowed** requests whose timestamp `t` falls in the sliding window `(T - W, T]`, where `W` is the configured window.
   - If that count is **less than** `Q`, the request is allowed.
   - Otherwise, the request is rejected with reason `"QUOTA_EXCEEDED"`.
3. An allowed request is recorded in the client's log. A rejected request is counted toward the client's rejected total but is **not** added to the allowed log.

---

## Window

- The window length `W` is configurable at `RateLimiter` construction time. The parameter is in **seconds** (default 60 seconds).
- Internally, timestamps are compared in **integer milliseconds**.
- The window is **half-open**: a prior request with timestamp exactly `T - W` is **not** in the current window; one with timestamp `T` (the current moment) **is**.

---

## Batch Close

- `close_batch()` closes the billing cycle. After close, no new requests may be processed; `request`, `register`, and `suspend` must raise `RateLimitError`.
- Closing twice raises `RateLimitError`.
- The returned `Batch` is a **frozen snapshot** of client state at close time. Later mutations to the limiter's internal state must not affect the batch.

---

## Pricing

The target function `compute_bill(batch) -> Bill` applies these rules to a closed batch.

### Tier (based on allowed-request count)

| Allowed count         | Tier         | Per-request rate (cents) |
|----------------------|--------------|--------------------------|
| `0 <= allowed < 100`  | `"starter"`    | 15                       |
| `100 <= allowed < 1000` | `"standard"`   | 10                       |
| `allowed >= 1000`     | `"enterprise"` | 5                        |

### Per-client cost

- **Suspended clients** are charged a flat **1000 cents** reactivation fee, regardless of their allowed count or rejected count. Their tier is reported as `"suspended"`.
- **Non-suspended clients** are charged `rate * allowed_count + 2 * rejected_count`, where `rate` is their tier rate from the table above.

### Totals

- `Bill.total_cents` is the sum of all line-item costs.
- All monetary values are **integer cents**. There are no fractional cents.

---

## Example

A batch closes with three clients:

| Client | Quota | Suspended | Allowed | Rejected |
|--------|-------|-----------|---------|----------|
| Alice  | 5     | no        | 3       | 1        |
| Bob    | 10    | yes       | 0       | 0        |
| Carol  | 100   | no        | 200     | 5        |

Computed bill:

- Alice: `starter`, cost = `15 * 3 + 2 * 1` = **47 cents**.
- Bob: `suspended`, cost = **1000 cents**.
- Carol: `standard`, cost = `10 * 200 + 2 * 5` = **2010 cents**.
- **Total: 3057 cents.**

---

## Data Model

You may use or extend the following types:

| Type | Fields |
|------|--------|
| `Decision` | `allowed: bool`, `reason: Optional[str]` |
| `ClientLog` | `client_id`, `quota`, `suspended`, `allowed_timestamps_ms`, `rejected_count` |
| `Batch` | `clients: Tuple[ClientLog, ...]` |
| `LineItem` | `client_id`, `tier`, `allowed_count`, `rejected_count`, `cost_cents` |
| `Bill` | `line_items`, `total_cents` |

---

## Required Interface

Your implementation must expose:

- **`RateLimiter`** — manages state and decisions.
  - `register(client_id, quota) -> None`
  - `suspend(client_id) -> None`
  - `request(client_id, timestamp_ms) -> Decision`
  - `close_batch() -> Batch`
- **`tier_for(allowed_count) -> str`** — return the tier name for a given allowed count.
- **`compute_bill(batch) -> Bill`** — compute the complete bill for a closed batch.

Raise `RateLimitError` for invalid operations (duplicate registration, unknown client, operations after close, double close).
