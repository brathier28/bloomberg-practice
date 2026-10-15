# Answer Key: Trade Settlement Netting

---

## 1. Spec to hand the candidate

Hand the candidate `problems/netting/spec.md` verbatim.

**One-line answer for "what does `net_obligations` do?"**
It groups all in-scope trades by (counterparty, currency, settlement_date), subtracts sell notionals from buy notionals within each group, and returns a `NettingRun` with the non-zero obligations and aggregate receive/pay totals.

---

## 2. Clarifying questions to expect

| Question | Answer to give | Bug it surfaces |
|---|---|---|
| What should happen if `net_obligations` is called on an unlocked book? | Raise `BookError`. | neutral (design gap) |
| Does the cutoff date include same-day settlement? | Yes — trades settling on the cutoff date are in scope. | Bug 1 |
| Are currency codes case-sensitive? (e.g., "usd" vs "USD") | Deflect: your call. | neutral |
| What order should obligations appear in the output? | Deflect: your call. | neutral |
| Can a book be re-locked or unlocked? | No — lock is one-way, locking twice raises `BookError`. | neutral |

**Mark as deflect:** at least two questions above say "your call." Look for the **assumption move**: "I'll assume X; I'll add a test so that assumption is explicit." If the candidate commits without a test, note it.

**Scoring note:** The cutoff-date question is highest value — it directly surfaces Bug 1. The unlocked-book question is the second most important because it defines the guard that `net_obligations` must check.

---

## 3. Codebase overview

| File | Purpose |
|---|---|
| `spec.md` | Problem specification |
| `question.py` | Implementation with planted bugs |
| `conftest.py` | Fixtures: `fresh_book`, `make_book`, `make_trade_group` |
| `test_netting_shipped.py` | Pre-shipped tests |
| `test_netting.py` | Candidate test file |
| `sample_run.py` | Happy-path demo |

**Key fixture:** `make_book()` creates a `TradeBook` with a default cutoff of 2026-10-20 and a controllable ID source. `make_trade_group(counterparty, currency, date, buys=[], sells=[])` builds a list of `Trade` objects directly — useful for testing `_net_signed` and `_build_obligation` without going through the book.

**Starting state commands:**

```bash
# Inside problems/netting/
pytest test_netting_shipped.py -v
# Expected: 13 passed, 4 failed (NotImplementedError)

pytest test_netting.py -v
# Expected: no tests collected (empty file)
```

---

## 4. Verify the map

After the AI maps the codebase, the candidate should verify these claims in the code. Ask "how do you know that's true?" for any the candidate skips.

1. Does `_is_in_scope` use `<=` or `<` for the cutoff comparison? (Answer: `<` — Bug 1.)
2. Does `lock()` store a copy of the trade list, or a reference to it? (Answer: a reference — Bug 5.)
3. Does `add_trade` check `self._locked` before creating the trade? (Answer: no — Bug 4.)
4. Does `_net_signed` subtract sell notionals or add them? (Answer: adds — Bug 3.)

---

## 5. Bug reference

### Bug 1 — Boundary / off-by-one

**Spec claim:** "Only trades with `settlement_date` on or before `cutoff_date` are included."

**Code seam:** `_is_in_scope`, line 162:
```python
return trade.settlement_date < cutoff
```

**Hypothesis:** The comparison uses strict less-than, so a trade settling on the cutoff date is excluded instead of included.

**Failing test (given / when / then):**
> Given a trade with `settlement_date = date(2026, 10, 20)` and a book with `cutoff_date = date(2026, 10, 20)`, when `_is_in_scope` is called, then it returns `True`.

```python
def test_trade_settling_on_cutoff_date_is_in_scope(make_book):
    cutoff = date(2026, 10, 20)
    trade = Trade("T1", "ALPHA", "USD", "buy", 100_000, date(2026, 10, 20))
    assert _is_in_scope(trade, cutoff) is True
```

**Good prompt:** "The spec says trades settling on or before the cutoff are in scope. Check `_is_in_scope` against that rule. Do not edit anything."

**Minimal fix:**
```python
return trade.settlement_date <= cutoff
```

**Why the test proves the fix:** The test inputs use `settlement_date == cutoff_date`. The old code returns `False` because `date == date` is not `<`. The fixed code returns `True` because `<=` matches equality. Any other comparison operator would change the result.

**Probing questions:**
- "What does the shipped test `test_trade_before_cutoff_is_in_scope` use as its date?" 2026-10-15 — five days before the cutoff, so it passes with either `<` or `<=`.
- "What would happen if you used `>=` instead?" You'd include only cutoff-day and future trades — the inverse of the intent.

---

### Bug 2 — Representation / format

**Spec claim:** "`amount_cents` in a `NetObligation` is always a non-negative integer."

**Code seam:** `_build_obligation`, line 204 (pay branch):
```python
        amount_cents=net,
```

**Hypothesis:** The function stores the raw signed net directly, so when `net < 0` the obligation carries a negative `amount_cents` instead of its absolute value.

**Failing test (given / when / then):**
> Given a signed net of −300,000 (we owe), when `_build_obligation` is called, then `amount_cents` is a non-negative integer (300,000).

```python
def test_pay_obligation_amount_cents_is_non_negative():
    key = ("BRAVO", "USD", date(2026, 10, 20))
    ob = _build_obligation(key, -300_000)
    assert ob.amount_cents >= 0
    assert ob.amount_cents == 300_000
```

**Good prompt:** "The spec says amount_cents is always non-negative. Check `_build_obligation` against that rule for a negative net. Do not edit anything."

**Minimal fix:**
```python
        amount_cents=abs(net),
```

**Why the test proves the fix:** `abs(-300_000)` is `300_000 > 0`. The old code stores `-300_000`, which fails the `>= 0` assertion. The fix makes the assertion pass regardless of which direction is involved.

**Probing questions:**
- "Why doesn't the positive branch need `abs(net)`?" `net > 0` is already positive; `abs` is a no-op there.
- "Why didn't the shipped test `test_negative_net_produces_pay_obligation` catch this?" It only checks `direction == "pay"`, not `amount_cents`. That was a deliberate gap in the shipped suite.

---

### Bug 3 — Wrong semantics (passes the happy path)

**Spec claim:** "The signed net = sum of buy notionals − sum of sell notionals."

**Code seam:** `_net_signed`, line 174:
```python
    return buys + sells
```

**Hypothesis:** The function correctly separates buy and sell totals but adds them instead of subtracting, so any group containing sells produces an inflated positive net rather than the correct difference.

**Failing test (given / when / then):**
> Given a group with one buy of 700,000 and one sell of 400,000, when `_net_signed` is called, then the result is 300,000 (not 1,100,000).

```python
def test_buy_and_sell_group_nets_to_difference_not_sum(make_trade_group):
    trades = make_trade_group(
        "ALPHA", "USD", date(2026, 10, 15), buys=[700_000], sells=[400_000]
    )
    assert _net_signed(trades) == 300_000
```

**Good prompt:** "I want to test _net_signed with a mixed buy/sell group. Add a test that verifies a 700,000 buy and a 400,000 sell in the same group nets to 300,000."

**Minimal fix:**
```python
    return buys - sells
```

**Why the test proves the fix:** With the bug, the result is 700,000 + 400,000 = 1,100,000. With the fix, it is 700,000 − 400,000 = 300,000. The shipped tests pass on the buggy code because they only use buy trades — `sells` is always 0, so `buys + 0 == buys - 0`.

**Probing questions:**
- "Why did the shipped tests miss this?" All shipped `_net_signed` tests pass `buys=` only. `sells` is always 0, making `+` and `-` indistinguishable.
- "What would a pure-sell group return with the buggy code?" A positive number — as if we were receiving instead of paying. The direction field would still say "pay" (set in `_build_obligation` based on the sign), but Bug 2 may also be in play, compounding the wrong output.

---

### Bug 4 — Missing state guard

**Spec claim:** "After locking, no further trades may be added; attempting to do so raises `BookError`."

**Code seam:** `add_trade`, lines 107–134 — no lock check before the direction validation at line 121.

**Hypothesis:** `add_trade` validates direction and notional but never checks `self._locked`, so trades can be silently appended to a locked book.

**Failing test (given / when / then):**
> Given a locked book, when `add_trade` is called, then `BookError` is raised and no trade is appended.

```python
def test_locked_book_rejects_new_trade_with_book_error(make_book):
    book = make_book()
    book.lock()
    with pytest.raises(BookError):
        book.add_trade("ALPHA", "USD", "buy", 50_000, date(2026, 10, 15))
    assert len(book._trades) == 0
```

**Good prompt:** "The spec says adding a trade to a locked book raises BookError. Write a test that proves the current code either raises or doesn't, then stop."

**Minimal fix:** Insert before the direction check at line 121:
```python
        if self._locked:
            raise BookError("cannot add trades to a locked book")
```

**Why the test proves the fix:** `pytest.raises(BookError)` fails if the call returns normally (as it does with the bug). After the fix the guard fires first. The `len(book._trades) == 0` assertion ensures the trade wasn't appended before the error — important because the guard must come before any state mutation.

**Probing questions:**
- "Why must the guard come before the direction check?" If direction validation ran first and passed, the trade object would be created and appended before the lock check could fire. With Bug 5 also unfixed, that trade would also be visible through `locked_trades`.
- "Does Bug 5 interact with Bug 4?" Yes — if both are unfixed, a trade added after lock leaks directly into `locked_trades` because it aliases the live list.

---

### Bug 5 — Aliasing / mutable reference

**Spec claim:** "The book records a frozen snapshot of the trade list at lock time. Modifications to the book's internal state after locking must not alter the snapshot."

**Code seam:** `lock()`, line 148:
```python
        self._locked_trades = self._trades
```

**Hypothesis:** The lock stores a reference to the live list, not a copy. Any later mutation of `self._trades` — whether from a bug (Bug 4 unfixed) or via direct internal access — is immediately reflected in `locked_trades`.

**Failing test (given / when / then):**
> Given a locked book, when a `Trade` is appended directly to the book's internal `_trades` list, then `locked_trades` is unchanged.

```python
def test_locked_trades_snapshot_is_unaffected_by_internal_mutation(make_book):
    book = make_book()
    book.add_trade("ALPHA", "USD", "buy", 100_000, date(2026, 10, 15))
    book.lock()
    count_at_lock = len(book.locked_trades)

    extra = Trade("X1", "BRAVO", "GBP", "buy", 50_000, date(2026, 10, 16))
    book._trades.append(extra)

    assert len(book.locked_trades) == count_at_lock
```

**Good prompt:** "The spec says the locked snapshot must not be affected by later changes. Write a test that appends to the book's internal list after locking and verifies `locked_trades` is unchanged."

**Minimal fix:**
```python
        self._locked_trades = tuple(self._trades)
```

**Why the test proves the fix:** A `tuple` is immutable and a separate object from the source list. Appending to `self._trades` after locking cannot affect the tuple. With the bug, `self._locked_trades` is the same object as `self._trades`, so `len()` reflects the mutation.

**Probing questions:**
- "Why `tuple(...)` instead of `list(self._trades)`?" Both copy, but a list can still be mutated. `frozen=True` on the dataclass only prevents reassigning the field, not mutating a list stored inside it. A `tuple` also matches the `Tuple[Trade, ...]` type hint on `locked_trades`.
- "How does this interact with Bug 4?" If both bugs are unfixed, `add_trade` silently appends after lock, and `locked_trades` reflects it immediately. Fixing either bug independently limits the blast radius; fixing both closes the hole completely.

---

## 6. Grading rubric

### Tests (strongest signal — panel called this out explicitly)

| Signal | Pass / Fail |
|---|---|
| Every fix is proven by a test that would fail on the old code | Pass |
| Test names state the spec guarantee (BDD form) | Pass |
| `amount_cents` boundary tested with a negative net | Pass |
| Cutoff-date boundary tested at `settlement_date == cutoff_date` | Pass |
| Zero-net exclusion tested | Pass |
| Candidate writes no tests, or tests only pass on both old and new code | **Fail** |
| Test written against implementation internals ("check `self._locked` is True") instead of spec behavior | **Fail** |

**Strong-pass (practice standard):** Test written and run *before* the fix — interviewer sees it fail, then sees the fix make it pass. (suggested)

### Ownership and process

| Signal | Pass / Fail |
|---|---|
| Treats the codebase as their own product | Pass |
| When a gap is deflected ("your call"), uses the assumption move | Pass |
| Checks in with the interviewer before the first patch and before implementing `net_obligations` | Pass |
| Follows the debug loop (spec → seam → hypothesis → explain → fix → test) | Pass |
| Verifies the AI's map by opening the functions it named | Pass |
| Says "AI told me so" and patches without checking | **Fail** |
| Skips check-ins entirely | **Fail** |

**Instant fail:** "Fix the problem," "solve it," or "find everything" as a prompt. No constraint, no boundary.

### Knowing what the code does

The interviewer should ask these questions (see individual bug sections for expected answers):

- Bug 1: "Why doesn't the shipped test catch this?"
- Bug 3: "What does the buggy code return for a pure-sell group?"
- Bug 5: "Why `tuple` instead of `list`?"
- Target function: "Why does `net_obligations` need `book.locked_trades` instead of the pool's live list?"

A candidate who can answer these demonstrates they read and understood the code, not just directed the AI.

### Prompts

| Signal | Pass / Fail |
|---|---|
| Every prompt has a goal and a boundary ("do not edit", "do not patch", "only list") | Pass |
| Mapping prompt says "do not edit" and "do not list issues" | Pass |
| Prompt narrows scope to one function or one spec rule | Pass |
| "Fix the problem" / "solve it" / "find everything" — no constraint | **Fail** |

### Narration

| Signal | Pass / Fail |
|---|---|
| States the expected output before running a test ("I expect it to return 300,000") | Pass |
| Explains the test in given/when/then form when writing it | Pass |

### Simplicity

| Signal | Pass / Fail |
|---|---|
| Each fix is 1–3 lines | Pass |
| No floating-point arithmetic introduced | Pass |
| `net_obligations` implementation uses the helpers provided | Pass |

---

## 7. Target function guide

### Algorithm

1. Check that `book.is_locked`; raise `BookError` if not.
2. For each trade in `book.locked_trades`, filter with `_is_in_scope(trade, book.cutoff_date)`.
3. Group passing trades into a dict keyed by `(trade.counterparty, trade.currency, trade.settlement_date)`.
4. For each group, call `_net_signed(group_trades)`. Skip if result is zero.
5. Call `_build_obligation(key, net)` to get a `NetObligation`.
6. Accumulate `total_receive_cents` (when `net > 0`) and `total_pay_cents` (when `net < 0`, use `abs(net)`).
7. Return `NettingRun(obligations=tuple(obligations), total_receive_cents=..., total_pay_cents=...)`.

### Reference implementation

```python
def net_obligations(book: TradeBook) -> NettingRun:
    if not book.is_locked:
        raise BookError("book must be locked before netting")

    groups: Dict[Tuple[str, str, date], List[Trade]] = {}
    for trade in book.locked_trades:
        if not _is_in_scope(trade, book.cutoff_date):
            continue
        key = (trade.counterparty, trade.currency, trade.settlement_date)
        groups.setdefault(key, []).append(trade)

    obligations = []
    total_receive = 0
    total_pay = 0
    for key, group_trades in groups.items():
        net = _net_signed(group_trades)
        if net == 0:
            continue
        obligations.append(_build_obligation(key, net))
        if net > 0:
            total_receive += net
        else:
            total_pay += abs(net)

    return NettingRun(
        obligations=tuple(obligations),
        total_receive_cents=total_receive,
        total_pay_cents=total_pay,
    )
```

### Probing questions on `net_obligations`

- **"Why `book.locked_trades` instead of the live trade list?"** The locked snapshot was taken at `lock()` time. If any trade was added after lock (Bug 4 unfixed), it would appear in the live list but not in the snapshot. The spec says netting runs on the snapshot.
- **"What happens if you call it before locking?"** The `locked_trades` property returns `None`, so iterating it raises `TypeError`. The guard catches this cleanly before touching the trades.
- **"What does `groups.setdefault(key, [])` do?"** Returns an existing list for that key, or inserts and returns an empty list. Equivalent to `if key not in groups: groups[key] = []` then `groups[key]`.
- **"Why `tuple(obligations)` at the end?"** `NettingRun.obligations` is typed `Tuple[NetObligation, ...]`. The `list` used during construction needs to be frozen before storing in the immutable dataclass field.
- **"What if all groups net to zero?"** `obligations` stays empty, both totals stay 0, and `NettingRun(obligations=(), total_receive_cents=0, total_pay_cents=0)` is returned — no error.

### Worked numbers (from spec.md example)

| Group key | Buys | Sells | Net | direction | amount_cents |
|---|---|---|---|---|---|
| ALPHA / USD / 2026-10-18 | 1,200,000 | 500,000 | +700,000 | receive | 700,000 |
| ALPHA / EUR / 2026-10-19 | 750,000 | 0 | +750,000 | receive | 750,000 |
| BRAVO / USD / 2026-10-20 | 0 | 300,000 | −300,000 | pay | 300,000 |
| ALPHA / USD / 2026-10-21 | 400,000 | — | excluded (after cutoff) | — | — |

`total_receive_cents` = 700,000 + 750,000 = **1,450,000**  
`total_pay_cents` = 300,000

**BDD tests for `net_obligations`:**

- Given the spec example book (locked), when `net_obligations` is called, then `total_receive_cents` is 1,450,000 and `total_pay_cents` is 300,000.
- Given a trade settling after the cutoff, when `net_obligations` is called, then that trade produces no obligation.
- Given a group where buys equal sells, when `net_obligations` is called, then that group is excluded from obligations.
- Given an unlocked book, when `net_obligations` is called, then `BookError` is raised.

---

## 8. Red flags (suggested)

### Prompt red flags
- No constraint on the first mapping prompt ("read the code and explain it").
- Broad scope: "find all the bugs," "fix everything that's wrong."
- No narration before running tests — candidate is surprised by results.

### Testing red flags
- Shipping tests pass `test_netting_shipped.py -v` and candidate doesn't notice the 4 failures.
- Tests that check internal state (`assert book._locked is True`) instead of observable behavior.
- No test for the cutoff boundary (the most spec-specific edge in this problem).
- No test for a sell trade in `_net_signed` (Bug 3 goes undetected).
- Tests written after the fix (can't see them fail first).

### Code red flags
- Implementing netting logic from scratch instead of calling `_net_signed` and `_build_obligation`.
- Using `float` for amounts anywhere.
- Implementing `net_obligations` before any bugs are fixed — correct output is impossible until at least Bugs 1, 3, and 5 are fixed.

### Process red flags
- Asking the AI to "map the codebase" but not opening the functions it points to.
- Patching a bug the AI volunteered without writing an exposing test first.
- Never checking in with the interviewer.
- Spending more than 5 minutes on the spec without asking a single clarifying question.

---

## 9. Timing guide (suggested)

| Phase | Clock time |
|---|---|
| Read spec + clarifying questions | 0–5 min |
| Map the codebase via the AI, then verify | 5–10 min |
| Find and fix bugs, one at a time (each fix proven by a test) | 10–25 min |
| Implement `net_obligations` (tests before implementation) | 25–40 min |
| Validate + wrap up | 40–45 min |

**Expected check-ins:** before the first patch, and before starting `net_obligations`.

**Soft pivot, minute 25:** if 3 or more bugs are fixed with tests, move the candidate to `net_obligations`.

**Hard pivot, minute 30:** move the candidate on regardless of bug count, so `net_obligations` gets at least 10 minutes.

**Fair nudges** (at most two, before the soft pivot):
- Bug 1: "What does the spec say about same-day settlement? Is there a test for that exact case?"
- Bug 3: "What does the spec say the net should be when there are both buys and sells? Does a test verify that?"
- Process: "You have about 25 minutes left. What would you prioritize?"

Never name a function or line number for a bug the candidate hasn't surfaced yet.
