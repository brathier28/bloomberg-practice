# FX Desk — Daily Settlement

## Overview

A currency clearing desk accepts FX conversion requests during an open window.
Each request converts a notional amount in a foreign currency to USD. When the
desk closes, it locks in the mid-rates for all submitted pairs and produces a
settlement report.

---

## Submission rules

- A request specifies a **participant** name (string), a **currency pair**
  (e.g. `"EURUSD"`), and a **notional** in source-currency cents (positive
  integer).
- Requests may only be submitted while the desk is **open**. Submitting to a
  closed desk raises `DeskError`.
- Each submission is a separate, independent request. Two requests with the
  same participant and pair are both processed.

---

## Rate and fee tier

The mid-rate for a pair is provided by an injectable callable:

```
rate_source(pair: str) -> int
```

It returns integer **basis points** (bps), where `10_000 bps = 1.0000 USD per
unit of source currency`. For example, `10_842` means 1.0842 USD per EUR.

A **spread** is added based on the individual request's notional:

| Tier | Notional (source cents) | Spread (bps) |
|------|------------------------|--------------|
| 1 – Small  | < 1,000,000            | 50           |
| 2 – Mid    | 1,000,000 to 9,999,999 | 20           |
| 3 – Large  | ≥ 10,000,000           | 5            |

- **All-in rate** = mid-rate + spread (in bps).
- **USD cost** = `notional × all-in rate ÷ 10,000`, using **integer (floor)
  division**. Money is always integer cents.

---

## Close and settlement

- `close()` locks the desk. It looks up the mid-rate for every submitted pair
  at that moment, stores them in the session snapshot, and returns a `Session`.
  No further submissions are accepted after close.
- `plan_settlement(session)` computes a `SettlementReport`:
  - One `Settlement` record per request.
  - `total_usd_cents`: sum of all USD costs.
  - `rollover_cents`: `seed_cents − total_usd_cents`. May be negative if costs
    exceed the seed (a shortfall).

---

## Data model

| Name | Type | Description |
|------|------|-------------|
| `ConversionRequest` | frozen dataclass | `id` (str), `participant` (str), `pair` (str), `notional_cents` (int) |
| `Session` | frozen dataclass | `requests` (tuple), `seed_cents` (int), `rates` (dict: pair → mid-rate bps, locked at close) |
| `Settlement` | frozen dataclass | `request_id` (str), `participant` (str), `pair` (str), `notional_cents` (int), `spread_bps` (int), `usd_cents` (int) |
| `SettlementReport` | frozen dataclass | `settlements` (tuple), `total_usd_cents` (int), `rollover_cents` (int) |

---

## Required interface

```python
desk = Desk(seed_cents=10_000_000, rate_source=my_rate_fn)
req  = desk.submit("Alice", "EURUSD", 500_000)
session = desk.close()
report  = plan_settlement(session)
```

---

## Target function

```
plan_settlement(session: Session) -> SettlementReport
```

Given a locked session, compute one `Settlement` per request and return
the full `SettlementReport`.

---

## Worked example

Seed: 10,000,000 cents ($100,000). Rate source: `EURUSD = 10,842 bps`.

| Participant | Notional (cents) | Tier | Spread | All-in rate | USD cost (cents) |
|-------------|-----------------|------|--------|-------------|-----------------|
| Alice       | 500,000         | 1    | 50 bps | 10,892 bps  | 544,600          |
| Bob         | 2,000,000       | 2    | 20 bps | 10,862 bps  | 2,172,400        |

- Alice: `500,000 × 10,892 ÷ 10,000 = 544,600`
- Bob: `2,000,000 × 10,862 ÷ 10,000 = 2,172,400`
- Total: `2,717,000`
- Rollover: `10,000,000 − 2,717,000 = 7,283,000`
