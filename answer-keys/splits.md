# Tab Split — Answer Key

---

## 1. Spec to hand the candidate

Hand the candidate `problems/splits/spec.md` verbatim.

**One-line answer for "what does `plan_splits` do?"**
It takes a recorded expense and returns a `SplitPlan` showing each participant's share in integer cents — base share from floor division, with one extra cent per remainder participant in join order.

---

## 2. Clarifying questions to expect

| Question | Answer to give | Bug it surfaces |
|---|---|---|
| "What does two-digit zero-padded mean for IDs?" | Explain: "00", "01", ..., "10". First joiner is always "00". | Bug 2 |
| "Does join order mean the order `add_participant` was called?" | Yes, insertion order is the canonical join order. | Bugs 3, 2 |
| "If two participants have the same name, do they each get their own share?" | Yes. Same name does not mean same person. | Bug 3 |
| "Can a closed tab have participants added to it?" | No, `add_participant` on a closed tab raises `SplitTabError`. Already coded. | Bug 4 (adjacent) |
| "Can an expense be split among a subset of participants?" | **Deflect: your call.** The spec says all current participants. Look for the assumption move. | neutral |
| "What if `total_cents` is zero?" | **Deflect: your call.** Look for the assumption move. | neutral |
| "What happens if there are no participants when an expense is recorded?" | **Deflect: your call.** | neutral |

**Scoring note:** The question about duplicate names is the highest-signal clarifying question — it surfaces Bug 3 directly. A candidate who asks it before looking at the code shows strong spec-reading. The subset question or zero-amount question are neutral but show thoroughness. The assumption move on any deflect earns credit; "I'll assume X and add a test" earns more than just "I'll assume X."

---

## 3. Codebase overview

| File | Purpose |
|---|---|
| `question.py` | All implementation: `SplitTab`, `_spread_remainder`, `count_payers`, `plan_splits` stub |
| `conftest.py` | `fresh_tab`, `make_tab`, `make_expense` fixtures |
| `test_splits_shipped.py` | 16 pre-shipped tests |
| `test_splits.py` | Candidate test file (empty) |
| `sample_run.py` | Happy-path demo |

**Key fixture — `make_expense`:** Builds an `Expense` directly from known values, bypassing `SplitTab`. Useful for testing `plan_splits` and `count_payers` in isolation with precise participant order and IDs.

**Starting state:**

```shell
pytest test_splits_shipped.py -v
# 12 passed, 4 failed (NotImplementedError in TestShippedPlanSplits)
```

---

## 4. Verify the map

After the AI maps the codebase, ask the candidate to verify:

1. Does `add_participant` zero-pad the participant ID to two digits?
2. Does `record_expense` snapshot the participants at call time, or store a reference?
3. Does `count_payers` return the raw length of `expense.participants`, or does it do anything else?
4. Does `_spread_remainder` distribute to the first `remainder` elements, or fewer?

The mock interviewer can ask "how do you know that's true?" for any of these.

---

## 5. Bug reference

### Bug 1 — Boundary / off-by-one

**Spec claim:** "The number of top-up recipients equals `total_cents mod n`."

**Code seam:** `_spread_remainder`, line 211: `for i in range(remainder - 1):`

**Hypothesis:** When `remainder` is 1 or more, `range(remainder - 1)` distributes one fewer extra cent than required, so the total distributed falls short by exactly 1 cent for remainder=1, 1 cent for remainder=2, etc.

Actually: `range(remainder - 1)` runs for `remainder - 1` iterations, so exactly one fewer participant receives an extra cent. With remainder=1, `range(0)` → zero iterations → nobody gets the extra cent.

**Failing test (given/when/then):**
> Given 2 participants and an expense of 101 cents, when `plan_splits` is called, then `total_distributed` equals 101 and one participant receives 51 cents.

```python
def test_remainder_cent_is_distributed_to_first_joiner(make_expense):
    expense = make_expense(101, [("Alice", "p0"), ("Bob", "p1")])
    plan = plan_splits(expense)
    assert plan.total_distributed == 101
    assert plan.splits[0].amount_cents == 51
    assert plan.splits[1].amount_cents == 50
```

**Good prompt:**
> "In `_spread_remainder`, trace what happens when `remainder` is 1. What does the loop execute? Do not edit files."

**Minimal fix:**
```python
for i in range(remainder):  # was: range(remainder - 1)
```

**Why the test proves the fix:** The test checks `total_distributed == 101`, which can only pass if every cent is accounted for. The old code leaves one cent unassigned, making the total 100.

**Probing questions:**
- "What is `range(0)` in Python?" An empty range; no iterations. So when remainder=1, nobody gets the extra cent.
- "Why does `_spread_remainder` take `remainder` as a parameter instead of computing it?" Separation of concerns — the caller already has the remainder from the division; passing it avoids recomputing `total_cents % n` inside the helper.

---

### Bug 2 — Representation / format

**Spec claim:** "Each participant receives a unique two-digit zero-padded identifier reflecting their join order: first joiner is `'00'`, second is `'01'`, tenth is `'10'`."

**Code seam:** `SplitTab.add_participant`, line 128: `participant = Participant(id=str(self._counter), name=name)`

**Hypothesis:** `str(0)` produces `"0"` (one character), not `"00"`. The first nine participants produce single-digit IDs. From the eleventh participant onward, IDs like `"10"` sort lexicographically before `"2"`, which corrupts any sort-by-ID ordering.

**Failing test (given/when/then):**
> Given a new tab, when a participant is added, then their ID is exactly two characters long and equals `"00"`.

```python
def test_first_participant_id_is_zero_zero(fresh_tab):
    p = fresh_tab.add_participant("Alice")
    assert p.id == "00"
```

**Good prompt:**
> "Read the spec rule for participant IDs. In `add_participant`, show me the line that generates the ID. Do not edit anything."

**Minimal fix:**
```python
participant = Participant(id=f"{self._counter:02d}", name=name)
```

**Why the test proves the fix:** The test asserts `p.id == "00"` exactly. The old code produces `"0"`, which fails. After the fix, `f"{0:02d}"` → `"00"`.

**Probing questions:**
- "Why does the format matter for sorting?" `"10" < "2"` in lexicographic order, so any code that sorts participants by ID to determine join order will treat the eleventh joiner as third.
- "What happens to the second participant's ID under the bug?" `str(1)` → `"1"`. All single-digit participants' IDs compare correctly against each other — so the bug is silent for tabs with nine or fewer participants.

---

### Bug 3 — Wrong semantics

**Spec claim:** "Two participants may share the same display name. Each is an independent person and receives their own share of every expense."

**Code seam:** `count_payers`, line 237: `return len({p.name for p in expense.participants})`

**Hypothesis:** Building a set of names deduplicates participants who share a name, so `count_payers` undercounts when any two participants have the same display name.

**Failing test (given/when/then):**
> Given two participants both named `"Alex"` on the same tab, when `count_payers` is called on an expense that includes both, then it returns 2.

```python
def test_count_payers_with_duplicate_names_counts_each_independently(fresh_tab):
    fresh_tab.add_participant("Alex")
    fresh_tab.add_participant("Alex")
    expense = fresh_tab.record_expense("Coffee", 200)
    assert count_payers(expense) == 2
```

**Good prompt:**
> "Compare the spec rule about duplicate names against `count_payers`. Give me the smallest input that would expose a violation. Do not patch anything."

**Minimal fix:**
```python
return len(expense.participants)
```

**Why the test proves the fix:** The set `{"Alex", "Alex"}` has length 1 (dedup). `len(expense.participants)` for two participants is 2. The test asserts 2.

**Probing questions:**
- "Why does the set dedup by name rather than by ID?" Python sets use the object's `__hash__` and `__eq__`. For a frozen dataclass, equality is field-by-field. Two `Participant` objects with the same `id` and `name` would be equal — but in practice `add_participant` always increments the counter, so two `"Alex"` participants have different IDs and are not equal as dataclasses. However, the set comprehension only hashes the `p.name` string, not the full `Participant` — so it deduplicates on name alone regardless of ID.
- "Does this bug affect the happy path?" No — as long as all display names are unique (the common case), `{p.name for p in ...}` and `len(expense.participants)` return the same value.

---

### Bug 4 — Missing state guard

**Spec claim:** "Attempting to record an expense on a closed tab raises `SplitTabError`."

**Code seam:** `SplitTab.record_expense`, line 157: the method body starts with `expense = Expense(...)` — no guard before it.

**Hypothesis:** Without a check for `self._closed`, `record_expense` silently creates and stores an expense even after the tab is closed.

**Failing test (given/when/then):**
> Given a closed tab, when `record_expense` is called, then `SplitTabError` is raised and no new expense is added to the tab.

```python
def test_recording_expense_on_closed_tab_raises_and_leaves_expenses_unchanged(fresh_tab):
    fresh_tab.add_participant("Alice")
    fresh_tab.record_expense("Lunch", 1000)
    fresh_tab.close_tab()
    with pytest.raises(SplitTabError):
        fresh_tab.record_expense("Dinner", 2000)
    assert len(fresh_tab.expenses) == 1
```

**Good prompt:**
> "The spec says recording on a closed tab should raise `SplitTabError`. Trace what `record_expense` does when `self._closed` is True. Do not patch anything."

**Minimal fix:** Add at the top of `record_expense`, before `expense = Expense(...)`:
```python
if self._closed:
    raise SplitTabError("Cannot record expense on a closed tab.")
```

**Why the test proves the fix:** `pytest.raises(SplitTabError)` fails if no exception is raised. The assertion on `len(fresh_tab.expenses) == 1` verifies the guard fires before any state mutation.

**Probing questions:**
- "Why does the guard need to come before `expense = Expense(...)`?" If it came after, an Expense object would already have been constructed and possibly appended before the error — leaving the tab in an inconsistent state.
- "`close_tab` has the double-close guard but `record_expense` does not — why?" That is the bug. `close_tab` was guarded correctly; `record_expense` was overlooked.

---

### Bug 5 — Aliasing / mutable reference

**Spec claim:** "Once recorded, the participant snapshot and total are fixed: adding more participants afterward does not change past expenses."

**Code seam:** `SplitTab.record_expense`, line 161: `participants=self._participants`

**Hypothesis:** `self._participants` is a mutable list. Storing the list directly means `expense.participants` and `self._participants` point to the same object. Adding participants afterward silently grows the expense's participant list.

**Failing test (given/when/then):**
> Given an expense recorded with 2 participants, when a 3rd participant is added afterward, then `expense.participants` still contains exactly 2 participants.

```python
def test_expense_participants_are_frozen_at_record_time(fresh_tab):
    fresh_tab.add_participant("Alice")
    fresh_tab.add_participant("Bob")
    expense = fresh_tab.record_expense("Dinner", 3000)
    fresh_tab.add_participant("Carol")
    assert len(expense.participants) == 2
```

**Good prompt:**
> "In `record_expense`, what is the type of the value assigned to `participants` in the `Expense` constructor? What does that mean for mutation after the call?"

**Minimal fix:**
```python
participants=tuple(self._participants),  # was: self._participants
```

**Why the test proves the fix:** With the bug, `len(expense.participants)` is 3 after adding Carol (the same list object grew). With the fix, `tuple(self._participants)` creates an immutable snapshot at call time, so the count stays 2.

**Probing questions:**
- "The `Expense` dataclass is frozen — why doesn't that protect the list?" `frozen=True` prevents reassigning `expense.participants = something_else`. It does not deep-freeze the object stored in that field. A list inside a frozen dataclass is still mutable.
- "Why `tuple(...)` rather than `list(self._participants)`?" Both copy, but a list can still be mutated. A tuple is truly immutable and also matches the `Tuple[Participant, ...]` type annotation.

---

## 6. Grading rubric

### Tests (strongest signal)

| Signal | Pass | Strong pass (suggested) |
|---|---|---|
| Writes tests before or alongside patches | Writes any test that exercises the fixed behavior | Writes the failing test first, sees it fail, then patches |
| BDD test names | Test name states the spec behavior being verified | Name is in given/when/then form |
| Tests boundary conditions | Tests the remainder=1 and remainder=0 cases separately | Tests remainder > 1 |
| Tests the assumption move | Writes a test for any assumed behavior | Names the assumption in the test and in narration |

**Instant fail:** Running tests without stating what they should return first ("I expect it to fail because...").

### Ownership and process

| Signal | Pass | Strong pass (suggested) |
|---|---|---|
| Assumption move | "I'll assume X" | "I'll assume X; here's the test that makes that assumption explicit" |
| Verifies the AI's map | Opens the function after the AI points to it | "The AI says X — let me confirm" before accepting |
| Debug loop | Spec claim → seam → hypothesis → fix → test | Test written before fix, then observed to fail |
| Checks in with interviewer | At least one check-in before starting target function | Check-in before first patch, check-in before implementing |

### Knowing what the code does

Expect these questions at any time. See "Probing questions" under each bug for expected answers.

- "What does `range(0)` return?"
- "Why does `frozen=True` on the dataclass not protect the list inside it?"
- "What happens if you pass `f"{counter:02d}"` vs `str(counter)` for the first ten participants?"
- "What does the set comprehension `{p.name for p in ...}` do differently from `len(expense.participants)`?"

### Prompts

| Pass | Fail |
|---|---|
| Goal + boundary: "Read X. Only do Y. Do not Z." | "Fix the bugs." |
| Targeted: "Compare this spec rule against this function." | "Find everything wrong." |
| Scope-limited edit: "Patch only this function." | "Solve the problem." |

### Narration

| Pass | Fail |
|---|---|
| "I expect this test to fail because..." | Running tests silently |
| "The spec says X; the code does Y" | No spec reference |

### Simplicity

All five fixes are one to three lines. An if-statement guard, a format string, a `range()` argument, a `len()` call, and `tuple(...)`. If the candidate proposes a refactor, ask "is there a simpler change?"

---

## 7. Target function guide

### Algorithm

1. Call `count_payers(expense)` → `n`.
2. If `n == 0`, return an empty `SplitPlan` with `total_distributed = 0`.
3. `base = expense.total_cents // n`
4. `remainder = expense.total_cents % n`
5. Build `amounts = [base] * n`.
6. Call `_spread_remainder(amounts, remainder)` — mutates in place.
7. Build one `Split` per participant in `expense.participants` order, using `amounts[i]`.
8. Return `SplitPlan(splits=..., total_distributed=sum of amounts)`.

### Reference implementation

```python
def plan_splits(expense: Expense) -> SplitPlan:
    n = count_payers(expense)
    if n == 0:
        return SplitPlan(splits=(), total_distributed=0)
    base = expense.total_cents // n
    remainder = expense.total_cents % n
    amounts = [base] * n
    _spread_remainder(amounts, remainder)
    splits = tuple(
        Split(
            participant_id=p.id,
            participant_name=p.name,
            amount_cents=amounts[i],
        )
        for i, p in enumerate(expense.participants)
    )
    return SplitPlan(
        splits=splits,
        total_distributed=sum(s.amount_cents for s in splits),
    )
```

**Dependency chain:** A correct `plan_splits` still produces wrong results until Bug 1 (`_spread_remainder`), Bug 3 (`count_payers`), and Bug 5 (snapshot) are all fixed.

### Probing questions

- "What happens if `n == 0`?" Division by zero. The guard returns an empty plan early. Ask: "what should `total_distributed` be in that case?"
- "Why `//` instead of `/`?" `/` produces a float. Money stays in integer cents.
- "Why `sum(s.amount_cents for s in splits)` instead of `expense.total_cents`?" After floor division, `_spread_remainder` distributes every cent exactly. The sum should always equal `total_cents`, but computing it from the splits makes the invariant explicit and testable.
- "What does `enumerate(expense.participants)` give you?" Pairs of `(index, Participant)`. The index is used to look up the per-participant amount in `amounts`.

### Worked numbers

| Participant | Join order | base | top-up | total |
|---|---|---|---|---|
| Zoe | 1st (index 0) | 333 | +1 | **334** |
| Alice | 2nd (index 1) | 333 | +1 | **334** |
| Bob | 3rd (index 2) | 333 | 0 | **333** |

Input: 1001 cents, 3 participants. `1001 // 3 = 333`, `1001 % 3 = 2`. Sum = 1001.

### BDD tests for `plan_splits`

- **Given** 3 participants in Zoe/Alice/Bob join order and an expense of 1001 cents, **when** `plan_splits` is called, **then** Zoe gets 334, Alice gets 334, Bob gets 333, and `total_distributed` is 1001.
- **Given** 2 participants and an expense of 101 cents, **when** `plan_splits` is called, **then** `total_distributed` equals 101.
- **Given** 3 participants and an expense of 300 cents (no remainder), **when** `plan_splits` is called, **then** each participant receives exactly 100 cents.
- **Given** two participants named `"Alex"` and an expense of 200 cents, **when** `plan_splits` is called, **then** `total_distributed` is 200 and each Alex receives 100 cents.
- **Given** an expense with zero participants, **when** `plan_splits` is called, **then** `splits` is empty and `total_distributed` is 0.

---

## 8. Red flags (suggested)

### Prompt
- Asking the AI to "find all bugs" in one shot.
- No boundary in the prompt ("fix `record_expense`" without "don't touch anything else").
- Accepting the AI's map without verifying the functions it named.

### Testing
- Only testing the happy path (unique names, evenly divisible amounts).
- Writing tests after the fix without first seeing them fail.
- Checking implementation details (`p.id[0] == "0"`) instead of spec behavior (`p.id == "00"`).

### Code
- Reimplementing `count_payers` logic inside `plan_splits` instead of calling it.
- Using `/` (float division) instead of `//`.
- Rebuilding `total_distributed` as `expense.total_cents` without verifying the sum.

### Process
- Spending more than 5 minutes on the spec without clarifying questions.
- Never checking in with the interviewer.
- Losing the thread mid-bug and switching to implementation before all bugs are addressed.

---

## 9. Timing guide (suggested)

| Phase | Clock time |
|---|---|
| Read spec + clarifying questions | 0–5 min |
| Map codebase via AI, then verify | 5–10 min |
| Find and fix bugs, one at a time | 10–25 min |
| Implement `plan_splits` | 25–40 min |
| Validate + wrap up | 40–45 min |

**Expected check-ins:** before the first patch, and before starting `plan_splits`.

**Soft pivot, minute 25 (suggested):** If 3 or more bugs are fixed with tests, move the candidate to `plan_splits`.

**Hard pivot, minute 30 (suggested):** Move the candidate to `plan_splits` regardless of bug count, so the function gets at least 10 minutes.

**If the candidate asks to move on after 3 clean fixes,** agree. That is good time management.

**Pacing (suggested):** 3 or more bugs fixed with tests by minute 25 is on track.

**Fair nudges (at most two, all before the soft pivot):**

- If the candidate hasn't found Bug 3: "What does the spec say about two participants with the same name?"
- If the candidate hasn't found Bug 4: "What does the spec say happens when you record an expense after the tab is closed?"
- Process nudge: "You have about 25 minutes left. What would you prioritize?"

Never name a function or line number for a bug the candidate hasn't found.
