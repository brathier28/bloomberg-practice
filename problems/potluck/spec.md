# Pot Luck — Fundraiser Drawing System

## Overview

You are implementing the backend for a charity fundraiser called **Pot Luck**. Participants pay to enter a drawing. At draw time the system calculates a winning code, matches it against each entry, and distributes the pot according to a tiered prize table.

---

## Pot Calculation

- A sponsor seeds the pot with **$10,000** at the start.
- Each entry adds **$5** to the pot.
- The pot is calculated at draw time, not at entry time.
- All monetary values are tracked in **integer cents**. Fractional cents are never awarded; any remainder rolls over.

---

## Entry Codes

- Each participant receives a **randomly generated five-digit code** when they enter.
- Valid codes run from **00000 to 99999 inclusive**, with leading zeros preserved.
- Each code is assigned independently; duplicates are possible.
---

## Draw Mechanics

- Entries are accepted until the draw is closed.
- At draw time the system generates one **winning code** using the same five-digit format.
- The pool is closed immediately when the draw is initiated; no new entries may be added after that point.
- The set of entries used for payout calculations is a **fixed snapshot** taken at the moment the draw closes.
---

## Match Counting

- A match is a **positional** comparison: position 0 of the entry code against position 0 of the winning code, position 1 against position 1, and so on.
- Repeated digits are treated like any other digit; there is no deduplication.
- A code with all five positions matching scores 5; a code with none matching scores 0.

---

## Prize Tiers

| Matches | Tier percentage |
|---------|----------------|
| 5       | 100%            |
| 4       | 40%             |
| 3       | 20%             |
| 2       | 5%              |
| 1       | nothing         |
| 0       | nothing         |

- Tiers are processed from highest (5) to lowest (2).
- All winners in the same tier **split that tier's amount equally** (integer cents each; remainder rolls over).
- If any entry achieves a 5-match, that entry (or those entries) receives the full pot and **no lower tier is paid**.
- Any amount not awarded rolls over to the next drawing.

---

## Example

Four entries enter. At draw time the pot is $10,020 (sponsor $10,000 + 4 × $5).

- Three entries match 4 digits → they split 40% of $10,020 = $4,008.00, each receiving $1,336.00.
- One entry matches 2 digits → receives 5% of $10,020 = $501.00.
- Remaining $5,511.00 rolls over.

---

## Data Model

You may use or extend the following types:

| Type | Fields |
|------|--------|
| `Entry` | `id`, `participant`, `code` |
| `Draw` | `winning_code`, `pot_cents`, `entries` |
| `Payout` | `entry_id`, `participant`, `match_count`, `amount_cents` |
| `PayoutPlan` | `payouts`, `awarded_cents`, `rollover_cents` |

---

## Required Interface

Your implementation must expose:

- **`FundraiserPool`** — manages state, entry registration, and draw closure.
  - `enter(participant) -> Entry` — register a participant and return their entry.
  - `close_draw() -> Draw` — close entries, compute the pot, generate a winning code, and return the draw.
- **`count_matches(entry_code, winning_code) -> int`** — return the number of positional matches.
- **`plan_payouts(draw) -> PayoutPlan`** — compute the full payout plan from a closed draw.

Raise `FundraiserError` for invalid operations (e.g., entering after the draw closes, closing an already-closed draw).
