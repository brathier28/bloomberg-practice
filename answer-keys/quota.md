# Quota — Interviewer Answer Key

Mock-interviewer cheat sheet for `problems/quota/`. Do not read this during a
timed run.

---

## 1. Spec to hand the candidate

Hand them `problems/quota/spec.md` as-is.

**One-liner for "what does the target function do?":** `compute_bill(batch)`
assigns each client a pricing tier based on allowed-request count, charges per
request at the tier rate plus a per-rejection penalty, overrides with a flat
suspension fee for suspended clients, and returns the full per-client bill
plus the total.

---

## 2. Clarifying questions to expect

| Question | Answer to give | Bug it surfaces |
|---|---|---|
| What happens if a client makes requests with duplicate timestamps? | Spec says timestamps are monotonically **non-decreasing**, so duplicates are permitted. Each duplicate is a separate request. | Bug 3 (set-dedup in `_in_window`) |
| Can quota be zero? | **Deflect: your call.** The spec doesn't say. Look for the assumption move. | neutral |
| Is the window inclusive at the lower edge? | Half-open: a prior timestamp exactly at `T - W` is **not** in the window. | neutral (bounds the window boundary question) |
| What timestamp units does the API accept? | Spec says milliseconds. The `RateLimiter` constructor takes `window_seconds`; comparisons are in ms internally. | Bug 2 (unit mismatch in `__init__`) |
| Should rejected requests be stored in the batch's timestamp log? | No. Rejected requests only increment `rejected_count`; they are not added to `allowed_timestamps_ms`. | neutral |
| What is the tier at exactly 100 allowed? Exactly 1000? | 100 → `"standard"`. 1000 → `"enterprise"`. (Boundaries are half-open: `< 100`, `< 1000`.) | Bug 1 (`tier_for` upper edge) |
| Does suspension zero out existing allowed requests? | No. The flat suspension fee **overrides** per-request pricing; the allowed log is irrelevant for the suspended line item. | neutral |

**Scoring note.** The strongest questions here are the unit question (surfaces
Bug 2 before any code is read) and the tier boundary question (surfaces Bug 1
the same way). Also credit the candidate for calling out the duplicate-timestamp
question even if they don't connect it to a bug yet — it's the single most
useful BDD scaffold for Bug 3.

The deflected question is "can quota be zero?". Candidate should respond with
the **assumption move**: "I'm going to assume quota is a positive integer and
add a test that enforces that."

---

## 3. Codebase overview

| File | What's in it |
|---|---|
| `spec.md` | Full spec. |
| `question.py` | Buggy implementation; target `compute_bill` is `NotImplementedError`. |
| `test_quota_shipped.py` | 18 shipped tests. |
| `test_quota.py` | Empty — candidate adds tests here. |
| `conftest.py` | `fresh_limiter`, `make_limiter`, `make_batch` fixtures. |
| `sample_run.py` | Happy-path demo. |

**Key fixture:** `make_batch(clients)` builds a `Batch` directly from a list
of dicts, bypassing `RateLimiter`. Use it when writing exposing tests for
`compute_bill` so you don't have to drive the limiter end-to-end.

**Starting state:**

```bash
$ pytest test_quota_shipped.py --tb=no -q
# 14 passed, 4 failed
# The 4 failures are TestShippedComputeBill (NotImplementedError).
```

---

## 4. Verify the map

After the AI maps the codebase, the candidate should open the file and
confirm these claims. Prompt: "How do you know that's true?"

- Does `RateLimiter.__init__` convert `window_seconds` into milliseconds before storing?
- Does `_in_window` count duplicates (two requests at the same ms count as two)?
- Does `request` reject calls made after `close_batch()`?
- Does the `Batch`'s `allowed_timestamps_ms` field hold a tuple (immutable), or a reference to the live internal list?

---

## 5. Bug reference

Debug-loop order: boundary, representation, semantics, state guard, aliasing.

### Bug 1 — `tier_for` upper-edge off-by-one

- **Spec claim:** "`enterprise`: 1000 or more allowed requests."
- **Code seam:** `tier_for`, line 247: `if allowed_count <= 1000:`
- **Hypothesis:** The upper edge of the `standard` tier is inclusive, so `allowed_count == 1000` returns `"standard"` instead of `"enterprise"`.
- **Failing test:** Given `allowed_count == 1000`, when `tier_for` is called, then it returns `"enterprise"`.
  ```python
  def test_tier_for_1000_allowed_is_enterprise():
      assert tier_for(1000) == "enterprise"
  ```
- **Good prompt:** "In question.py, compare `tier_for` against the tier table in spec.md section Pricing. List any boundary values where the code and the spec disagree. Do not patch anything."
- **Minimal fix:** `if allowed_count <= 1000:` → `if allowed_count < 1000:`
- **Why the test proves the fix:** 1000 is exactly the lower edge of `"enterprise"` per the spec table. If the fix is wrong in the other direction (`< 999`), 999 would wrongly become enterprise; the shipped `test_moderate_count_is_standard` and this test together pin the boundary.
- **Probing questions:**
  - "Why is 1000 the right boundary?" The spec table defines `"enterprise"` as `allowed >= 1000`. Using `<` makes `tier_for(1000)` fall through to the `return "enterprise"` branch.
  - "What's the impact of this bug on the bill?" A heavy-usage client gets charged 10 ¢ per request instead of 5 ¢ — their line item is 2× too high.

### Bug 2 — `__init__` stores `window_seconds` as `_window_ms` without converting

- **Spec claim:** "The window length `W` is configurable… The parameter is in seconds (default 60 seconds). Internally, timestamps are compared in integer milliseconds."
- **Code seam:** `RateLimiter.__init__`, line 115: `self._window_ms: int = window_seconds`
- **Hypothesis:** The constructor assigns the seconds value directly to `_window_ms`, making the effective window 1000× too short.
- **Failing test:** Given a limiter with `quota=1` and `window_seconds=60`, when two requests arrive at `t=0` and `t=100` (ms), then the second is rejected with `QUOTA_EXCEEDED` (buggy: allowed, because 100 ms is outside the 60 ms effective window).
  ```python
  def test_second_request_100ms_later_is_rejected_within_quota_one_and_60s_window():
      limiter = RateLimiter(window_seconds=60)
      limiter.register("alice", quota=1)
      assert limiter.request("alice", 0).allowed is True
      d = limiter.request("alice", 100)
      assert d.allowed is False and d.reason == "QUOTA_EXCEEDED"
  ```
- **Good prompt:** "In `RateLimiter.__init__`, the parameter is `window_seconds` but the attribute is `_window_ms`. Point me at the conversion, and if there isn't one, write a failing test that exposes the gap. Do not patch yet."
- **Minimal fix:** `self._window_ms = window_seconds * 1000`
- **Why the test proves the fix:** 100 ms is well inside a 60-second window but outside a 60-ms one. After the fix, `cutoff = 100 - 60000 = -59900`, so `t=0` is in the window and the second request is correctly rejected.
- **Probing questions:**
  - "Why don't the shipped tests catch this?" They all use timestamps spaced ≤ 10 ms with wide quotas — both the 60-ms buggy window and the 60-second correct window produce the same decisions.
  - "What's a stress test that would also expose this?" One request per second for a few minutes with a tight quota: correct impl rejects as soon as the window fills; buggy impl never rejects because each request is 1000 ms past the last.

### Bug 3 — `_in_window` dedupes with a set

- **Spec claim:** "Repeated… timestamps are monotonically non-decreasing per client" (duplicates are permitted and each counts).
- **Code seam:** `_in_window`, line 126: `return len({t for t in timestamps_ms if t > cutoff})`
- **Hypothesis:** The set comprehension deduplicates identical timestamps, so N requests at the same ms are counted as 1.
- **Failing test:** Given `quota=2`, when three requests arrive with the same `timestamp_ms=100`, then the third is rejected with `QUOTA_EXCEEDED` (buggy: allowed, because `{100}` has length 1).
  ```python
  def test_third_request_at_same_timestamp_exceeds_quota_two():
      limiter = RateLimiter()
      limiter.register("alice", quota=2)
      assert limiter.request("alice", 100).allowed is True
      assert limiter.request("alice", 100).allowed is True
      d = limiter.request("alice", 100)
      assert d.allowed is False and d.reason == "QUOTA_EXCEEDED"
  ```
- **Good prompt:** "Compare `_in_window` to the spec rule for counting prior allowed requests in the window. Suggest one input that would expose any mismatch. Do not patch anything."
- **Minimal fix:** `return sum(1 for t in timestamps_ms if t > cutoff)`
- **Why the test proves the fix:** Three identical timestamps in the window should count as 3 for quota purposes. `sum` counts each occurrence; `len(set(...))` loses the duplicates.
- **Probing questions:**
  - "Why did someone reach for `set` here?" Likely a stray dedup instinct. The spec explicitly says timestamps may repeat, which this breaks.
  - "What if we added `assert len(timestamps_ms) == len(set(timestamps_ms))` at the top instead?" That turns a silent miscount into a loud assertion — but still rejects valid behavior. The right fix is to count without deduping.

### Bug 4 — `request` has no closed-cycle guard

- **Spec claim:** "After close, no new requests may be processed; `request`, `register`, and `suspend` must raise `RateLimitError`."
- **Code seam:** `request`, line 182: the method goes straight to `if client_id not in self._clients:` without first checking `self._batch`. `register` and `close_batch` both guard; `request` does not.
- **Hypothesis:** `request` accepts calls after close, silently mutating `_clients` and the already-aliased batch snapshot.
- **Failing test:** Given a closed batch, when `request` is called, then `RateLimitError` is raised and the batch's allowed-timestamp log is unchanged.
  ```python
  def test_request_after_close_raises_and_leaves_batch_unchanged():
      limiter = RateLimiter()
      limiter.register("alice", quota=5)
      batch = limiter.close_batch()
      with pytest.raises(RateLimitError):
          limiter.request("alice", 10)
      assert len(batch.clients[0].allowed_timestamps_ms) == 0
  ```
- **Good prompt:** "`register`, `suspend`, `close_batch`, and `request` are all state-mutating. For each, list whether it checks `self._batch` first. Do not patch anything."
- **Minimal fix:** Insert at the start of `request`:
  ```python
  if self._batch is not None:
      raise RateLimitError("Billing cycle is closed.")
  ```
- **Why the test proves the fix:** The spec guarantees the batch is frozen after close. Without the guard, a late `request` both bypasses the error AND (because of Bug 5) corrupts the batch's log. The fix stops the bypass before any mutation happens.
- **Probing questions:**
  - "Why does the guard go first, before the unknown-client check?" So a rejected request doesn't even get as far as touching state. With Bug 5 unfixed, order-of-operations matters.
  - "How does this interact with Bug 5?" With both bugs, calling `request` after close mutates the live `allowed_ts` list and the aliased batch field sees it. Fixing just Bug 5 would stop the leak into the batch; fixing just Bug 4 would stop the mutation. The spec requires both.

### Bug 5 — `close_batch` stores a live list reference

- **Spec claim:** "The returned `Batch` is a frozen snapshot of client state at close time. Later mutations to the limiter's internal state must not affect the batch."
- **Code seam:** `close_batch`, line 216: `allowed_timestamps_ms=s["allowed_ts"],`
- **Hypothesis:** `allowed_timestamps_ms` is typed as `Tuple[int, ...]` but is assigned the live mutable list from the limiter's internal dict. The frozen `ClientLog` dataclass only prevents reassignment, not mutation of the stored list.
- **Failing test:** Given a closed batch, when the limiter's internal `allowed_ts` list is appended to, then `batch.clients[0].allowed_timestamps_ms` is unchanged.
  ```python
  def test_closed_batch_is_isolated_from_later_internal_mutation():
      limiter = RateLimiter()
      limiter.register("alice", quota=5)
      limiter.request("alice", 10)
      batch = limiter.close_batch()
      before = tuple(batch.clients[0].allowed_timestamps_ms)
      limiter._clients["alice"]["allowed_ts"].append(99_999)
      assert tuple(batch.clients[0].allowed_timestamps_ms) == before
  ```
- **Good prompt:** "In `close_batch`, each `ClientLog` field is populated from the internal dict. Which fields are copied, and which are references? Do not patch anything."
- **Minimal fix:** `allowed_timestamps_ms=tuple(s["allowed_ts"]),`
- **Why the test proves the fix:** After the fix, the batch owns an independent tuple. Mutating the internal list cannot affect the batch, satisfying the spec's "frozen snapshot" guarantee.
- **Probing questions:**
  - "Why `tuple(...)` and not `list(s['allowed_ts'])`?" `list(...)` also copies, but a list can still be mutated later. `tuple` matches the dataclass's declared type and makes the field truly immutable.
  - "Would `frozen=True` on the dataclass alone fix this?" No — `frozen=True` only prevents reassignment of fields. It does nothing to a list stored inside a frozen dataclass.
  - "What does `compute_bill` depend on, from this bug's perspective?" It calls `len(cl.allowed_timestamps_ms)`. If that field is live, the computed bill reflects whatever the internal state happens to be at bill time, not at close time.

---

## 6. Grading rubric

### Tests (strongest signal)

| Pass | Fail |
|---|---|
| Writes a failing test before each patch. | Patches without a failing test, or writes the test after the fix. |
| Test names are BDD (given/when/then) and state the spec guarantee. | Test names describe implementation (`test_window_cutoff_variable_is_correct`). |
| Boundary tests first (edge values, empties, duplicates). | Only happy-path tests. |
| Narrates each test out loud in given/when/then form. | Silent while the AI writes tests. |

### Ownership and process

| Pass | Fail |
|---|---|
| Uses the **assumption move** when a question is deflected. | Repeats "your call" back to the AI or ignores the gap. |
| **Verifies the AI's map** by opening the file. | Trusts the AI's claim about `_in_window` without reading it. |
| Debug loop per bug: spec → code seam → hypothesis → failing test → fix → explanation. | Jumps to a patch; or runs the full suite instead of a targeted test. |
| **Checks in with the interviewer** before the first patch and before implementing `compute_bill`. | Treats the interviewer as absent. |

### Knowing what the code does

| Pass | Fail |
|---|---|
| Explains why `//` is used in cost math (integer cents, no fractional). | Introduces `/` or `round(...)` and shrugs when asked. |
| Explains why Bug 5 needs `tuple(...)` not `list(...)`. | "They're both copies, right?" without pursuing. |
| Can describe what happens when Bug 4 and Bug 5 interact. | Fixes one without noticing the other. |

### Prompts

| Pass | Fail |
|---|---|
| Prompts end with a **constraint** ("do not edit files", "do not patch anything", "list up to five"). | "Fix the problem." "Find everything." "Solve it." → **instant fail**. |
| Scopes prompts to one area or one claim. | Dumps the whole file in and asks for a review. |

### Narration

| Pass | Fail |
|---|---|
| Says "I expect this test to fail because…" before running. | Runs tests, then reacts. |

### Simplicity

| Pass | Fail |
|---|---|
| Fixes are 1–3 lines. If/else is fine. | Rewrites `_in_window` with a deque, or hoists a helper for a one-liner. |
| Keeps money in integer cents. | Introduces floats or `Decimal`. |

**Instant fail:** "fix the problem", "solve it", or "find everything" as a prompt.

---

## 7. Target function guide

### Algorithm

1. Walk `batch.clients` in order.
2. For each client, compute `allowed = len(cl.allowed_timestamps_ms)`.
3. If the client is **suspended**: `tier = "suspended"`, `cost = SUSPENSION_FEE_CENTS`.
4. Otherwise:
   - `tier = tier_for(allowed)`.
   - `cost = TIER_RATES_CENTS[tier] * allowed + REJECTION_PENALTY_CENTS * cl.rejected_count`.
5. Append a `LineItem(client_id, tier, allowed, rejected_count, cost)`.
6. Return `Bill(line_items=tuple(line_items), total_cents=sum(li.cost_cents for li in line_items))`.

### Reference implementation

```python
def compute_bill(batch: Batch) -> Bill:
    line_items = []
    for cl in batch.clients:
        allowed = len(cl.allowed_timestamps_ms)
        if cl.suspended:
            tier = "suspended"
            cost = SUSPENSION_FEE_CENTS
        else:
            tier = tier_for(allowed)
            cost = TIER_RATES_CENTS[tier] * allowed + REJECTION_PENALTY_CENTS * cl.rejected_count
        line_items.append(LineItem(
            client_id=cl.client_id,
            tier=tier,
            allowed_count=allowed,
            rejected_count=cl.rejected_count,
            cost_cents=cost,
        ))
    total = sum(li.cost_cents for li in line_items)
    return Bill(line_items=tuple(line_items), total_cents=total)
```

### Probing questions about specific lines

- **"Why `len(cl.allowed_timestamps_ms)` instead of a stored `allowed_count`?"**
  The `ClientLog` type has no `allowed_count` field — the log of timestamps is the single source of truth. If Bug 5 is unfixed, `len(...)` reflects whatever is in the aliased list at bill time, which demonstrates the dependency.

- **"What happens if you swap the `cl.suspended` branch to use `tier_for(allowed)` + `SUSPENSION_FEE_CENTS` added on top?"**
  The spec says the suspension fee **overrides** per-request pricing. Adding on top double-charges and breaks the `test_suspended_client_is_charged_flat_suspension_fee` shipped test.

- **"Why not use a dict comprehension and build `Bill` inline?"**
  Fine either way; the key is integer arithmetic (no `Decimal`, no float), tuple output for immutability, and preserving the order of `batch.clients`.

- **"What does `compute_bill` depend on from the bugs?"**
  - Bug 1 (`tier_for`): directly, via the `tier_for(allowed)` call.
  - Bug 5 (`close_batch` alias): directly, via `len(cl.allowed_timestamps_ms)` reading from a live list.

### Worked numbers

| Client | Quota | Suspended | Allowed | Rejected | Tier     | Cost (cents) |
|--------|-------|-----------|---------|----------|----------|--------------|
| Alice  | 5     | no        | 3       | 1        | starter    | 15·3 + 2·1 = 47 |
| Bob    | 10    | yes       | 0       | 0        | suspended  | 1000 |
| Carol  | 100   | no        | 200     | 5        | standard   | 10·200 + 2·5 = 2010 |
| **Total** |     |           |         |          |          | **3057** |

---

## 8. Red flags (suggested)

- **Prompt**: "fix all the bugs", "clean up the code", "make the tests pass".
- **Testing**: writing one all-in-one test that calls every public method; using `assert decision == Decision(True, None)` without naming the behavior; comparing against the implementation ("assert `self._window_ms == 60`") instead of the spec guarantee.
- **Code**: introducing `Decimal`, `float`, `collections.deque`, or timezone math; adding a `cached_property` on `ClientLog`; writing a helper that collapses three bug fixes into one method.
- **Process**: patching without re-running the targeted test; applying every AI suggestion without opening the file; silently accepting a "your call" and never writing a test around the assumption.

---

## 9. Timing guide (suggested)

| Phase | Target |
|---|---|
| Read spec + clarifying questions | 5 min |
| Map the codebase via the AI, then verify | 5 min |
| Diagnose bugs with targeted prompts | 15 min |
| Patch + test, one bug at a time | 10 min |
| Implement `compute_bill` | 8 min |
| Buffer | 2 min |

**Check-in moments:** before the first patch; before starting `compute_bill`.

**Fair nudges if stuck:**

- Before any bug: "What's the smallest input you could pass to `_in_window` that would surprise you?"
- Stuck on Bug 2: "The spec says `window_seconds=60`. What are the units of `self._window_ms` after `__init__`?"
- Stuck on Bug 4 vs 5 interaction: "If both bugs are live, what does `request('alice', 999)` do to the already-returned `batch`?"
- Stalled on target: "Walk me through what you'd compute for a single-client batch with 150 allowed and 2 rejected."

**Pacing (suggested):** 3+ bugs fixed with tests by minute 30 is on track. Clean process on fewer bugs is better than a scramble that fixes four without failing tests.
