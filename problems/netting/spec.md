# Trade Settlement Netting

## Overview

You are implementing the backend for a **bilateral trade settlement netting system**. Our firm records buy and sell trades against named counterparties throughout the day. At end-of-day, the system collapses all trades into a minimal set of net obligations — one net payment per (counterparty, currency, settlement date) group — reducing both settlement risk and the number of wire transfers required.

---

## Trades

- A **trade** records a single buy or sell of a currency amount against a named counterparty.
- Fields: `id` (unique string), `counterparty` (string), `currency` (three-letter code, e.g. `"USD"`), `direction` (`"buy"` or `"sell"`), `notional_cents` (non-negative integer), `settlement_date` (date).
- Trades are added to a **TradeBook**. The book raises `BookError` for invalid operations.

---

## Netting Scope

- The TradeBook has a `cutoff_date` set at creation.
- Only trades with `settlement_date` **on or before** `cutoff_date` are included in netting. Trades settling after the cutoff are ignored.

---

## Netting Rules

- Trades are grouped by the three-field key: **(counterparty, currency, settlement_date)**.
- Within each group, the **signed net** is computed as:

  ```
  net = sum of buy notionals − sum of sell notionals
  ```

  - Positive net → we **receive** that amount from the counterparty.
  - Negative net → we **pay** that amount to the counterparty.

- Groups with a net of exactly **zero** are excluded from the output.
- `amount_cents` in a `NetObligation` is always a **non-negative integer**. The `direction` field (`"receive"` or `"pay"`) carries the sign.

---

## Book Lifecycle

- Trades may be added while the book is **unlocked**.
- Calling `lock()` seals the book:
  - After locking, no further trades may be added; attempting to do so raises `BookError`.
  - The book records a **frozen snapshot** of the trade list at lock time. Modifications to the book's internal state after locking must not alter the snapshot.
- Netting is computed on a locked book.

---

## Example

Book `cutoff_date`: 2026-10-20.

| # | Counterparty | Currency | Direction | Notional (cents) | Settlement date |
|---|---|---|---|---|---|
| 1 | ALPHA | USD | buy | 1,200,000 | 2026-10-18 |
| 2 | ALPHA | USD | sell | 500,000 | 2026-10-18 |
| 3 | ALPHA | EUR | buy | 750,000 | 2026-10-19 |
| 4 | BRAVO | USD | sell | 300,000 | 2026-10-20 |
| 5 | ALPHA | USD | buy | 400,000 | 2026-10-21 |

Trade 5 settles after the cutoff and is **excluded**.

**Net obligations after locking and netting:**

| Counterparty | Currency | Settlement date | amount_cents | direction |
|---|---|---|---|---|
| ALPHA | USD | 2026-10-18 | 700,000 | receive |
| ALPHA | EUR | 2026-10-19 | 750,000 | receive |
| BRAVO | USD | 2026-10-20 | 300,000 | pay |

`total_receive_cents` = 1,450,000  
`total_pay_cents` = 300,000

---

## Data Model

| Type | Fields |
|---|---|
| `Trade` | `id`, `counterparty`, `currency`, `direction`, `notional_cents`, `settlement_date` |
| `NetObligation` | `counterparty`, `currency`, `settlement_date`, `amount_cents`, `direction` |
| `NettingRun` | `obligations`, `total_receive_cents`, `total_pay_cents` |

---

## Required Interface

- **`TradeBook(cutoff_date, ...)`** — manages trades and the lock lifecycle.
  - `add_trade(counterparty, currency, direction, notional_cents, settlement_date) -> Trade`
  - `lock() -> None` — seal the book and record a snapshot.
  - `is_locked` — boolean property.
  - `locked_trades` — the frozen snapshot (`Tuple[Trade, ...]`), or `None` before locking.
  - `cutoff_date` — the netting cutoff date.
- **`net_obligations(book: TradeBook) -> NettingRun`** — compute net obligations for a locked book.

Raise `BookError` for invalid operations (e.g., adding a trade after locking, locking an already-locked book).
