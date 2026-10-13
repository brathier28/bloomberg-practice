# Answer Key: FX Desk — Daily Settlement

---

## 1. Spec to hand the candidate

Hand the candidate `problems/fx/spec.md` verbatim.

**One-line answer for "what does the target function do?"**
`plan_settlement(session)` iterates over every request in the locked session,
computes each one's USD cost (notional × all-in rate ÷ 10,000), and returns a
`SettlementReport` with all settlements, the total, and the rollover.

---

## 2. Clarifying questions to expect

| Question | Answer to give | Bug it surfaces |
|----------|---------------|-----------------|
| What if the same pair is submitted twice by the same participant? | Each submission is a separate, independent request — both are settled. | Bug 3 (dedup) |
| What happens if `notional_cents` is zero or negative? | **Deflect: "Your call — what do you want to happen?"** Look for the assumption move: candidate should say "I'll assume it raises DeskError and add a test to make that assumption explicit." | Neutral (no bug) |
| What currency pairs are valid? | Trust the rate source; if it errors, let the exception propagate. | Neutral |
| Can the desk be closed more than once? | No — only one close per desk. | Neutral |

**Scoring note:** The zero/negative notional question is the one to deflect. The most valuable question is the same-pair-twice question — it touches Bug 3. A candidate who asks it and then checks the code is already ahead.

---

## 3. Codebase overview

| File | Key contents |
|------|-------------|
| `question.py` | `Desk` class, `_get_spread`, `_compute_usd_cost`, `_settle_requests`, `plan_settlement` stub |
| `conftest.py` | `desk` fixture (fresh Desk), `make_desk` factory (injectable rate source), `make_session` factory (builds Session directly) |
| `test_fx_shipped.py` | 18 tests: 14 pass, 4 fail with NotImplementedError |
| `test_fx.py` | Empty candidate file |

**Starting-state commands:**

```
cd problems/fx
pytest test_fx_shipped.py -v
```

Expected: **14 passed, 4 failed** (all 4 failures are `NotImplementedError` from
`TestShippedSettlementReport`).

**Key fixture:** `make_session` builds a `Session` directly from known values,
bypassing the `Desk`. Use it in `plan_settlement` tests to control exact
requests and rates without triggering any Desk bugs.

---

## 4. Verify the map

After the AI maps the codebase, ask the candidate to verify these claims in the
code. The interviewer can follow up with "how do you know that's true?"

1. Does `close()` store the live `_requests` list or a snapshot?
   *(Expected: live list — Bug 5.)*
2. Does `_get_spread` use `<` or `<=` for the Tier 3 boundary?
   *(Expected: `<=`, which is wrong — Bug 1.)*
3. Does `_compute_usd_cost` use `/` or `//`?
   *(Expected: `/` — Bug 2.)*
4. Does `submit()` check `self._session` before creating a request?
   *(Expected: no check — Bug 4.)*

---

## 5. Bug reference

Bugs are listed in debug-loop order (easiest to expose first).

---

### Bug 1 — Boundary / off-by-one

**Spec claim:** Tier 3 applies when `notional_cents ≥ 10,000,000`.

**Code seam:** `_get_spread`, line 112:
```python
if notional_cents <= LARGE_THRESHOLD:   # ← BUG: should be <
    return 20
```

**Hypothesis:** A notional of exactly `10,000,000` (the Tier 3 boundary) falls
into Tier 2 and gets 20 bps instead of 5 bps.

**Failing test (given/when/then):**
Given a notional of exactly 10,000,000 cents, when the spread is computed,
then it should be 5 bps. With the bug it is 20 bps.

```python
def test_tier3_boundary_notional_gets_5_bps_spread():
    assert _get_spread(10_000_000) == 5
```

**Good prompt:**
"In `question.py`, look only at `_get_spread`. Compare its tier boundaries against
the spec table. List any mismatch. Do not edit files."

**Minimal fix (1 line):**
```python
if notional_cents < LARGE_THRESHOLD:   # < not <=
```

**Why the test proves the fix:** `_get_spread(10_000_000)` returns 20 before
the fix and 5 after. The test is written against the spec boundary, not the
implementation.

**Probing questions:**
- "Why does this pass the happy-path tests?" Shipped tests use 5,000,000 (clearly
  mid-tier) and 15,000,000 (clearly large-tier) — neither hits the boundary.
- "What's the financial impact?" A $100,000 trade at the boundary pays 15 extra
  bps in spread — $150 more than specified.

---

### Bug 2 — Representation / format

**Spec claim:** USD cost = notional × all-in rate ÷ 10,000, using integer (floor)
division. Money is always integer cents.

**Code seam:** `_compute_usd_cost`, line 122:
```python
return notional_cents * all_in_rate / 10_000   # ← BUG: float division
```

**Hypothesis:** `/` produces a float. When the product is not evenly divisible
by 10,000, `usd_cents` is a fractional float, violating the integer-cents
invariant. Summing floats in `plan_settlement` makes `total_usd_cents` a float.

**Failing test (given/when/then):**
Given a notional of 100,001 cents and a rate of 10,000 bps (spread 50, all-in
10,050), when the USD cost is computed, then it equals 100,501 (floor) and is
an integer. With the bug it is `100501.005` (a float).

```python
def test_usd_cost_with_non_divisible_notional_is_integer_and_floored():
    result = _compute_usd_cost(100_001, 10_000, 50)
    assert isinstance(result, int)
    assert result == 100_501
```

**Good prompt:**
"In `question.py`, find `_compute_usd_cost`. Check whether the division operator
is consistent with the spec's 'integer floor division' rule. Do not edit files."

**Minimal fix (1 line):**
```python
return notional_cents * all_in_rate // 10_000
```

**Why the test proves the fix:** The non-divisible input forces a fractional
result with `/`, failing both `isinstance(result, int)` and the value check.
With `//` the result is the integer floor.

**Probing questions:**
- "Why do the shipped tests pass with the bug?" They use `100_000 * 10_050 =
  1,005,000,000` — divisible by 10,000, so the float happens to equal the
  integer and the `==` comparison passes.
- "What happens when `plan_settlement` sums floats?" `total_usd_cents` becomes
  a float, so `SettlementReport.total_usd_cents` is a float even though it's
  typed as `int`. Arithmetic downstream can accumulate rounding error.

---

### Bug 3 — Wrong semantics that pass the happy path

**Spec claim:** Each submission is a separate, independent request. Two requests
with the same participant and pair are both settled.

**Code seam:** `_settle_requests`, lines 134–136:
```python
seen: Dict = {}
for req in requests:
    seen[(req.participant, req.pair)] = req   # ← BUG: dedup, last wins
```

**Hypothesis:** The dict keyed by `(participant, pair)` silently discards all
but the last request when the same participant submits the same pair twice,
producing fewer settlements than there are requests.

**Failing test (given/when/then):**
Given Alice submits EURUSD twice, when `_settle_requests` is called, then two
Settlement records are returned. With the bug only one is returned.

```python
def test_two_requests_same_participant_same_pair_both_settled():
    r1 = ConversionRequest("id1", "Alice", "EURUSD", 500_000)
    r2 = ConversionRequest("id2", "Alice", "EURUSD", 2_000_000)
    result = _settle_requests((r1, r2), {"EURUSD": 10_000})
    assert len(result) == 2
```

**Good prompt:**
"In `question.py`, read `_settle_requests`. The spec says each request is
independent. Does this function settle every request in the input tuple?
For each gap, give the smallest input that would expose it. Do not edit files."

**Minimal fix (3 lines — remove the seen dict, iterate directly):**
```python
result = []
for req in requests:
    mid_rate = rates[req.pair]
    spread = _get_spread(req.notional_cents)
    usd = _compute_usd_cost(req.notional_cents, mid_rate, spread)
    result.append(Settlement(
        request_id=req.id,
        participant=req.participant,
        pair=req.pair,
        notional_cents=req.notional_cents,
        spread_bps=spread,
        usd_cents=usd,
    ))
return result
```

**Why the test proves the fix:** With the `seen` dict present, `len(result) ==
1` for the duplicate input. Without it, both requests are processed and
`len(result) == 2`.

**Probing questions:**
- "Why do the shipped tests pass?" They always use unique `(participant, pair)`
  combinations, so every key in `seen` is distinct and nothing is dropped.
- "Which request survives the dedup?" The last one inserted (Python dicts keep
  insertion order since 3.7), so the first request's ID and notional are silently
  lost.

---

### Bug 4 — Missing state guard

**Spec claim:** Submitting to a closed desk raises `DeskError`.

**Code seam:** `Desk.submit`, lines 78–85 — no guard before `ConversionRequest(...)`:
```python
def submit(self, participant, pair, notional_cents):
    # missing: if self._session is not None: raise DeskError(...)
    req = ConversionRequest(...)
    self._requests.append(req)
    return req
```

**Hypothesis:** Without the guard, `submit()` happily appends requests after
the desk is closed. With Bug 5 present, those requests also appear in the
already-returned session.

**Failing test (given/when/then):**
Given a closed desk, when `submit` is called, then `DeskError` is raised and
the session's request count is unchanged. With the bug no error is raised.

```python
def test_submit_after_close_raises_desk_error_and_leaves_session_unchanged():
    desk = Desk(seed_cents=10_000_000, rate_source=lambda pair: 10_000)
    desk.submit("Alice", "EURUSD", 500_000)
    session = desk.close()
    original_count = len(session.requests)
    with pytest.raises(DeskError):
        desk.submit("Bob", "GBPUSD", 1_000_000)
    assert len(session.requests) == original_count
```

**Good prompt:**
"In `question.py`, read `Desk.submit`. The spec says submissions are rejected
after close. Is there a guard? If not, write a test that calls submit after
close and verify its behavior. Do not edit files yet."

**Minimal fix (2 lines, at the top of submit):**
```python
if self._session is not None:
    raise DeskError("Desk is closed; no further submissions are accepted.")
```

**Why the test proves the fix:** Without the guard, `pytest.raises(DeskError)`
fails because no exception is raised. With the guard, DeskError is raised before
any request object is created.

**Probing questions:**
- "Why does the guard go first?" If the guard comes after `ConversionRequest(...)`,
  the request object is created and (with Bug 5 unfixed) appended to the session's
  live list before the error fires.
- "What happens if Bug 5 is still present when you fix this?" Existing post-close
  requests (submitted when the bug was present) still show up in the session, even
  after fixing Bug 4.

---

### Bug 5 — Aliasing / mutable reference

**Spec claim:** `close()` returns a frozen snapshot of the session. The session's
`requests` tuple is not affected by subsequent desk mutations.

**Code seam:** `Desk.close`, line 96:
```python
self._session = Session(
    requests=self._requests,    # ← BUG: live list reference
    ...
)
```

**Hypothesis:** `self._requests` is a list. Storing it directly in the frozen
`Session` dataclass means `session.requests` points to the same mutable list.
Any future mutation of `desk._requests` silently changes the session.

**Failing test (given/when/then):**
Given a closed session, when the desk's internal `_requests` list is mutated
directly, then `session.requests` is unchanged. With the bug its length grows.

```python
def test_closed_session_requests_unaffected_by_subsequent_desk_mutations():
    desk = Desk(seed_cents=10_000_000, rate_source=lambda pair: 10_000)
    desk.submit("Alice", "EURUSD", 500_000)
    session = desk.close()
    original_count = len(session.requests)
    desk._requests.append(
        ConversionRequest("extra", "Bob", "GBPUSD", 1_000_000)
    )
    assert len(session.requests) == original_count
```

**Good prompt:**
"In `question.py`, read `Desk.close`. The spec says it returns a frozen snapshot.
Does `session.requests` remain unchanged if `desk._requests` is mutated afterward?
Do not edit files."

**Minimal fix (1 line):**
```python
requests=tuple(self._requests),
```

**Why the test proves the fix:** With the list reference, `session.requests` is
the same object as `desk._requests`; appending to either changes both. After the
fix, `session.requests` is a new tuple — appending to the list leaves the tuple
untouched.

**Probing questions:**
- "Why `tuple(...)` instead of `list(self._requests)`?" Both copy, but a list can
  still be mutated later. `frozen=True` on the dataclass only prevents reassigning
  the field, not mutating a container inside it. A tuple is immutable and also
  matches the `Tuple[ConversionRequest, ...]` type hint.
- "Does this bug interact with Bug 4?" Yes. With Bug 4 present (no guard),
  post-close submissions are appended to `_requests`. Because Bug 5 stores the
  live list, those submissions also appear in the session — requests submitted
  after close silently infect the session snapshot.

---

## 6. Grading rubric

### Tests (strongest signal)

| Signal | Pass | Fail |
|--------|------|------|
| Writes a failing test before every patch | Demonstrates the bug exists, runs it, sees it fail | Patches first, writes test after (or never) |
| BDD test names | `test_large_threshold_notional_gets_tier3_spread` | `test_bug1` or `test_spread` |
| Narrates in given/when/then | States aloud: "Given notional 10,000,000, when spread is computed, then I expect 5 bps" | No narration or narrates "I'm testing the code" |
| Boundary conditions first | Writes the exact boundary value (10,000,000) | Writes a value like 11,000,000 that doesn't touch the boundary |
| Tests spec behavior, not implementation | Test checks `_get_spread(10_000_000) == 5` | Test checks `self._tier == 3` |

**Instant fail:** "AI, find all the bugs and fix them."

### Ownership and process

| Signal | Pass | Fail |
|--------|------|------|
| Assumption move on deflected question | "I'll assume zero notional raises DeskError; here's a test to make that explicit" | Accepts deflection and moves on without a test |
| Verifies the AI's map | Opens the file and reads the line the AI named | Takes the AI's summary at face value |
| Debug loop per bug | Spec claim → seam → hypothesis → failing test → fix → explain | Jumps straight to patching without a hypothesis |
| Checks in with interviewer | "I'm going to fix Bug 1 next — does that order make sense?" | Ignores the interviewer and works with the AI alone |

### Knowing what the code does

See probing questions in each bug's section above. The interviewer may ask any of
these at any point.

### Prompts

| Good | Bad |
|------|-----|
| "Read `_get_spread`. Compare its tier boundaries against the spec table. List any mismatch. Do not edit files." | "Fix the spread function." |
| "I want Tier 1/2/3 coverage. Are there gaps? Write a test for the Tier 3 boundary. Do not patch anything." | "Find all the bugs in the spread logic." |
| "Read `Desk.close`. Does it return a snapshot? If not, what input would expose it? Do not edit." | "Check if close is correct." |

### Simplicity

Pass: one-line fixes, plain `if` guards, `tuple(...)`.
Fail: refactoring `_settle_requests` into a class, introducing a copy helper,
using `dict.fromkeys` or `itertools.groupby` when a direct loop suffices.

---

## 7. Target function guide

### Algorithm

1. Call `_settle_requests(session.requests, session.rates)` to compute one
   `Settlement` per request.
2. Sum `s.usd_cents` over all settlements → `total_usd_cents`.
3. Return `SettlementReport(settlements=tuple(settlements), total_usd_cents=total, rollover_cents=session.seed_cents - total)`.

### Reference implementation

```python
def plan_settlement(session: Session) -> SettlementReport:
    settlements = _settle_requests(session.requests, session.rates)
    total = sum(s.usd_cents for s in settlements)
    return SettlementReport(
        settlements=tuple(settlements),
        total_usd_cents=total,
        rollover_cents=session.seed_cents - total,
    )
```

**Dependency on bugs:** a correct implementation still produces wrong output
until at least these are fixed:
- Bug 3 (`_settle_requests` deduplicates) — missing settlements
- Bug 5 (`session.requests` is a live list) — snapshot may be mutated before
  `plan_settlement` runs
- Bug 2 (float division) — `total_usd_cents` becomes a float
- Bug 1 (boundary) — wrong spread for boundary-notional requests

### Probing questions on `plan_settlement`

- "Why call `_settle_requests` instead of iterating inline?" It centralises
  the per-request logic, keeps `plan_settlement` focused on aggregation, and
  makes it easy to test `_settle_requests` independently.
- "What happens if the session has zero requests?" `_settle_requests` returns
  `[]`, `total = 0`, `rollover = seed_cents`. Correct: the full seed rolls over.
- "Why `tuple(settlements)` instead of leaving it as a list?" `SettlementReport`
  is a frozen dataclass; its `settlements` field is typed `Tuple[Settlement, ...]`.
  A tuple is also immutable, consistent with the snapshot pattern.
- "Can `rollover_cents` be negative?" Yes — if total USD costs exceed the seed.
  The spec explicitly allows a shortfall.

### Worked example

| Participant | Notional (cents) | Tier | Spread | All-in | USD cost |
|-------------|-----------------|------|--------|--------|----------|
| Alice       | 500,000         | 1    | 50 bps | 10,892 | 544,600  |
| Bob         | 2,000,000       | 2    | 20 bps | 10,862 | 2,172,400|

- Alice: `500,000 × 10,892 // 10,000 = 544,600`
- Bob: `2,000,000 × 10,862 // 10,000 = 2,172,400`
- Total: `2,717,000`
- Rollover: `10,000,000 − 2,717,000 = 7,283,000`

### BDD tests for `plan_settlement`

- Given a session with zero requests, when settlement is planned, then there are
  no settlements and rollover equals the seed.
- Given a session where Alice submits EURUSD twice, when settlement is planned,
  then there are two settlement records (one per request).
- Given the spec's worked example inputs, when settlement is planned, then
  `total_usd_cents == 2,717,000` and `rollover_cents == 7,283,000`.
- Given total USD costs that exceed the seed, when settlement is planned, then
  `rollover_cents` is negative.

---

## 8. Red flags (suggested)

**Prompt red flags**
- "Find all bugs and fix them." (Instant fail — no process, no tests.)
- "Is the code correct?" (Too broad; no constraint.)
- Asking the AI to summarize bugs in chat after fixing them. (Candidate may be
  the next session's candidate; don't let the answer escape.)

**Testing red flags**
- Writing tests only after patching.
- Test names like `test_bug1` or `test_spread_correct`.
- Tests that check internal state (`self._session is not None`) rather than
  observable behavior.
- No test for the exact boundary value (10,000,000).

**Code red flags**
- Using `/` for money division anywhere in a fix.
- Storing a list inside a frozen dataclass and calling it a snapshot.
- Introducing a deepcopy when `tuple(...)` suffices.

**Process red flags**
- Never checking in with the interviewer.
- Accepting the AI's map without opening the file.
- Implementing `plan_settlement` before fixing the helpers it depends on.

---

## 9. Timing guide (suggested)

| Phase | Target |
|-------|--------|
| Read spec + clarifying questions | 5 min |
| Map codebase via AI, then verify | 5 min |
| Diagnose bugs with targeted prompts | 15 min |
| Patch + test, one bug at a time | 10 min |
| Implement `plan_settlement` | 8 min |
| Buffer | 2 min |

**Check-in moments:** before the first patch ("I'm going to fix Bug 1 — does
that order make sense to you?"), and before implementing `plan_settlement`
("I've fixed the helpers; ready to implement the target function — good?").

**Fair nudges:**
- Minute 10, no bugs found: "Have you looked at the tier boundaries in
  `_get_spread`?"
- Minute 20, no test for Bug 3: "The spec says each request is independent.
  Have you tested what happens when the same participant submits the same pair
  twice?"
- Minute 30, `plan_settlement` not started: "You've fixed the helpers. What's
  the algorithm for `plan_settlement`?"

**Pacing (suggested):** 3 or more bugs fixed with tests by minute 30 is on
track. A clean process on fewer bugs beats a rushed fix of all five.
