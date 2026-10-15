# Tab Split — Group Expense Splitter

# Personal Notes

- Unique identifier -> Two digit zero-padded number -> How is this digit created? Is it some random generator? is it guaratneed that participants will have a unique ID, is there a max?; Sequential 

- Evenly in integer -> What happens to cents

- Display name -> not more than three

- Snapshot 

- Top-up assignment?
  - How does top-up assignment work? 




# tests to clarify 

- Adding participants -> test for 




## Overview

You are implementing the backend for **Tab Split**, a utility that tracks shared expenses for a group. Participants are added to a tab in join order. Whenever a shared bill is paid, it is recorded as an expense and split equally among all current participants in integer cents. The tab can be closed at any time; no further expenses may be recorded after that.


---

## Participants

- Participants are added to a tab in the order they join. Each participant receives a unique identifier that encodes their join sequence as a **two-digit zero-padded number**: the first joiner is `"00"`, the second is `"01"`, the tenth is `"10"`, and so on.
- A tab may have any number of participants.
- Two participants may share the same display name. Each is an independent person and receives their own share of every expense.

---

## Expenses

- An expense is recorded against **all participants currently on the tab** at the moment `record_expense` is called.
- The total is expressed in **integer cents**. Fractional cents are never used.
- Once recorded, the participant snapshot and total are **fixed**: adding more participants afterward does not change past expenses.

---

## Splitting

- The total is divided equally among the expense's participants using **integer (floor) division**.
- The **remainder** is `total_cents mod n` (where `n` is the number of participants). This remainder equals the number of **top-up recipients** — participants who each receive one extra cent.
- Top-up recipients are chosen in **join order**: the participant who joined earliest receives the first extra cent, the next-earliest receives the second, and so on, until all remainder cents are distributed.
- **Every cent** in the total is always distributed; there is no leftover.

---

## Lifecycle

- A tab starts **open**. Expenses and participants may be added freely.
- `close_tab()` closes the tab. Attempting to record an expense on a closed tab raises `SplitTabError`.
- Calling `close_tab()` on an already-closed tab raises `SplitTabError`.

---

## Example

A tab has three participants joined in this order: Zoe, Alice, Bob.
An expense of **$10.01** (1001 cents) is recorded.

- Base share: `1001 // 3 = 333` cents each.
- Remainder: `1001 % 3 = 2` cents → 2 top-up recipients.
- Top-up recipients (by join order): Zoe (1st) and Alice (2nd) each get 1 extra cent.

| Participant | Joined | Amount (cents) |
|-------------|--------|----------------|
| Zoe         | 1st    | 334            |
| Alice       | 2nd    | 334            |
| Bob         | 3rd    | 333            |

Total distributed: **1001 cents** ✓

---

## Data Model

| Type | Fields |
|------|--------|
| `Participant` | `id`, `name` |
| `Expense` | `id`, `description`, `total_cents`, `participants` |
| `Split` | `participant_id`, `participant_name`, `amount_cents` |
| `SplitPlan` | `splits`, `total_distributed` |

---

## Required Interface

Your implementation must expose:

- **`SplitTab`** — manages participants and expenses for a shared tab.
  - `add_participant(name) -> Participant` — register a participant and return their record.
  - `record_expense(description, total_cents) -> Expense` — record a shared expense against all current participants.
  - `close_tab() -> None` — close the tab.
- **`count_payers(expense) -> int`** — return the number of payers for an expense.
- **`plan_splits(expense) -> SplitPlan`** — compute the full split plan for an expense.

Raise `SplitTabError` for invalid operations.
