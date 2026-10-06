# Pot Luck Mock Interviewer Guide

## Spec to hand the candidate

Hand this over verbatim. Don't add examples, hints, or clarifications unprompted. Wait for the candidate to ask.

---

**Pot Luck**

You are building the backend for a charity fundraising drawing.

- The pot starts at $10,000 (sponsor seed) plus $5 per entry, calculated at drawing time.
- Each entry receives a randomly generated 5-digit code, from 00000 to 99999 inclusive.
- A winning code is generated at drawing time.
- Payout tiers by number of matching digits: 5 matches = 100% of pot, 4 = 40%, 3 = 20%, 2 = 5%. 1 match or fewer pays nothing.
- Winners in the same tier split that tier's amount equally.
- Tiers are processed from 5 down to 2.
- If any entry matches all 5 digits, that winner takes the entire pot and lower tiers receive nothing.
- Any amount not awarded rolls over to the next drawing.

**Example:** 3 entries match 4 digits and 1 entry matches 2 digits. Each 4-match entry receives 13.33% of the pot and the 2-match entry receives 5%.

**The candidate's task:** The codebase has been started. Review it, identify any issues, fix them, and implement `plan_payouts`.

**If asked about plan_payouts:** Say: "It takes a closed Draw and returns a PayoutPlan: the list of individual payouts, the total awarded, and the rollover amount."

## Clarifying questions to expect

These are the questions a prepared candidate should ask before touching the code. Answer each one as shown, except the one marked **Deflect**.

| Question | Answer to give | What it surfaces |
|---|---|---|
| Are matches positional by index, including repeated digits? | Yes, positional. 11111 vs 10101 = 3 matches. | Bug 3 |
| Are entries rejected after the draw closes? | Yes. Entering after close_draw raises FundraiserError. | Bug 4 |
| Are a closed draw's entries immutable? | Yes. The draw holds a frozen snapshot. | Bug 5 |
| Must every code be exactly 5 digits, including leading zeros? | Yes. 42 is stored as 00042. | Bug 2 |
| Can codes span the full range, 00000 to 99999 inclusive? | Yes, both ends must be reachable. | Bug 1 |
| If a split leaves cents, where do they go? | They roll over. Money is integer cents, never floats. | plan_payouts |
| Can one participant win with multiple entries? | **Deflect:** "Your call." | The assumption move |
| What if more than 100,000 people enter? | Depends on the spec version (see note below). | Neutral |

**The assumption move.** When you deflect, a strong candidate says something like: "I'm assuming one participant can win with several entries. I'll add a test so that assumption is explicit." Silently picking a behavior is a miss.

**Spec discrepancy to settle before the mock.** The workshop said a code is never given to two people, which makes more than 100,000 entries a real capacity gap. The `spec.md` in the codebase says duplicates are possible, which removes that gap. Pick one version. If you use the codebase's spec, answer "duplicates are fine."

**Scoring note (suggested):** asking about positional matching, closure, and the snapshot before reading any code is the strongest early habit.

## Codebase overview

The candidate receives these files. Only `question.py` and `test_potluck.py` need to be touched during the round.

| File | Purpose |
|---|---|
| `spec.md` | The problem spec. The candidate reads this first. |
| `question.py` | Implementation under review. Contains all 5 bugs. `plan_payouts` is stubbed with `raise NotImplementedError`. |
| `test_potluck_shipped.py` | Shallow pre-shipped tests that dodge every bug. The payout tests fail on the stub. |
| `test_potluck.py` | The candidate's test file. Should hold only imports and `# Add your tests here.` The original named skeleton gave away the bugs. |
| `conftest.py` | Fixtures: `fresh_pool`, `make_pool(random_source)`, `make_draw(winning_code, pot_cents, entries)`. |
| `sample_run.py` | Happy-path demo. Safe to run, reveals nothing about the bugs. |

**Key fixture:** `make_pool(lambda: 0.0)` creates a pool whose random source always returns 0.0. This is how boundary tests on code generation work without monkey-patching.

**Starting state to verify before the mock:**

- `pytest test_potluck_shipped.py -v`: 17 tests. 13 pass, and the 4 in `TestShippedPayoutPlan` fail with NotImplementedError until `plan_payouts` is written.
- `pytest test_potluck.py -v`: collects 0 tests.

## Verify the map

After the AI points to the relevant functions, the candidate should open them and check its claims. The workshop's phrase: "AI is a map, the repository is the territory." If they take the AI's summary on faith, ask "How do you know that's true?"

| Question to check in the code | Answer |
|---|---|
| Does the random range preserve both 00000 and 99999? | No. Bugs 1 and 2. |
| Does the closed draw hold a copied snapshot of the entries? | No. Bug 5. |
| Does payout code read the frozen pot from the draw? | Nothing to check yet, since `plan_payouts` is a stub. Check it in their implementation. |

## Bug reference

Each bug follows the debug loop the workshop taught: spec claim, code seam, hypothesis, failing test, minimal fix, then why the test proves it. The failing tests are written as given/when/then (BDD). Ask the probing question after each fix.

---

**Bug 1: 99999 can never be generated**

- **Spec claim:** Codes run from 00000 to 99999 inclusive.
- **Code seam:** `_generate_code()`, line 122: `number = int(self._random_source() * 99_999)`
- **Hypothesis:** The multiplier is one short, so the top code is unreachable.
- **Failing test:** Given a random source returning 0.999999, when an entry is created, then its code is "99999". The buggy code gives 99998.
- **Good prompt:** "I want codes from 00000 up to 99999 inclusive. Are there gaps? Add a test that verifies the upper boundary. Do not patch anything."
- **Minimal fix:** Multiply by `100_000`.
- **Why the test proves it:** 0.999999 is about the largest value the source can return. If it maps to 99999, the top of the range is reachable.
- **Probing question:** "Why 100,000 and not 99,999?" Expected: `random_source()` returns values in [0, 1), never 1, so multiplying by 99,999 tops out at 99,998.

---

**Bug 2: Codes lose leading zeros**

- **Spec claim:** Codes are five digits, with leading zeros preserved.
- **Code seam:** `_generate_code()`, line 123: `return str(number)`
- **Hypothesis:** Small numbers are converted to strings without padding.
- **Failing test:** Given a random source returning 0.000425 (which yields 42), when an entry is created, then its code is "00042". The buggy code gives "42".
- **Good prompt:** "Inject a random source that yields 42. What code does the entry get? Do not edit files."
- **Minimal fix:** `f"{number:05d}"` or `str(number).zfill(5)`.
- **Why the test proves it:** 42 needs three leading zeros. If it comes back as "00042", padding works for every short number.
- **Probing question:** "What does the winning code look like when the random value is 0?" Expected: "0" instead of "00000", so no entry could ever match all five positions.

---

**Bug 3: Matching ignores position and repeated digits**

- **Spec claim:** Matches are positional, and repeated digits aren't deduplicated.
- **Code seam:** `count_matches()`, line 212: `return len(set(entry_code) & set(winning_code))`
- **Hypothesis:** Set intersection checks which digits appear in both codes, not which positions line up.
- **Failing tests:** Given entry 11111 and winning code 10101, when matches are counted, then the result is 3 (buggy: 1). Also 12345 vs 54321 = 1 (buggy: 5) and 00000 vs 00000 = 5 (buggy: 1).
- **Good prompt:** "Compare count_matches against this rule: matches are positional by index, including repeated digits. Give the smallest inputs that would expose a violation. Do not patch anything."
- **Minimal fix:**

```python
def count_matches(entry_code, winning_code):
    if len(entry_code) != 5 or len(winning_code) != 5:
        raise ValueError("codes must be five characters")
    return sum(a == b for a, b in zip(entry_code, winning_code))
```

- **Why the tests prove it:** Each case breaks set logic a different way. Repeated digits collapse, reordered digits all count as matches, and an identical code of repeated digits scores 1.
- **Probing question:** "Why the length check?" Expected: `zip` stops silently at the shorter string, so a 4-character code would undercount with no error.

---

**Bug 4: Late entries accepted after the draw closes**

- **Spec claim:** No new entries after the draw closes.
- **Code seam:** `enter()`, lines 148-151. Nothing checks `self._draw` before `entry_id = str(uuid.uuid4())`.
- **Hypothesis:** `enter()` never looks at whether the draw is closed.
- **Failing test:** Given a closed draw, when someone enters, then `FundraiserError` is raised and the draw's entries and pot are unchanged.
- **Good prompt:** "Close the draw, then attempt one more entry. Add a test that checks FundraiserError is raised and the pot is unchanged. Do not patch anything yet."
- **Minimal fix:** First line of `enter()`: `if self._draw is not None: raise FundraiserError("draw already closed")`
- **Why the test proves it:** It checks both the rejection and the lack of side effects.
- **Probing question:** "Why does the guard go first?" Expected: otherwise a rejected entry still gets an id and a code and is appended to the pool's list. With Bug 5 unfixed, it would even leak into the closed draw.

---

**Bug 5: The draw holds a live list, not a frozen snapshot**

- **Spec claim:** The entries used for payouts are a fixed snapshot taken when the draw closes.
- **Code seam:** `close_draw()`, line 180: `entries=self._entries`
- **Hypothesis:** The draw stores a reference to the pool's list instead of a copy.
- **Failing test:** Given a closed draw, when the pool's entry list is appended to, then `draw.entries` is unchanged. Once Bug 4 is fixed, `enter()` raises after close, so this test has to append to `pool._entries` directly.
- **Good prompt:** "After close_draw, append directly to the pool's internal entry list. Does draw.entries change? Add a test for it. Do not patch anything."
- **Minimal fix:** `entries=tuple(self._entries)`
- **Why the test proves it:** Changing the source list after close is the only way the snapshot could drift. If `draw.entries` stays the same, it's a real copy.
- **Probing question:** "Why `tuple(...)` instead of `list(self._entries)`?" Expected: both copy, but a list can still be mutated later. `frozen=True` on the dataclass only stops reassigning the field, not changing a list inside it. A tuple also matches the `Tuple[Entry, ...]` type hint.

## Grading rubric

The round grades **how the candidate directs the AI**, not whether they reach the answer. The dimensions below follow the panel's own ranking: tests first, then ownership and process, then knowing what the code does.

**Instant fail:** any version of "fix the issue," "solve it," or "find everything." One panelist said that alone fails the interview.

---

**Dimension 1: Tests (the strongest signal)**

The panel called tests the most important part, more than once.

| Signal | Pass | Fail |
|---|---|---|
| Order | Writes a failing test before each patch | Patches first, tests after |
| Boundaries | Tests boundary conditions first, plus empty input | Starts with happy-path cases |
| BDD | Names and narrates tests as given/when/then from the spec | Tests implementation details, like checking a private field |
| Coverage | A test for every bug they fix | Leaves a fixed bug untested |
| Explanation | Says why each test proves the fix | Runs tests silently |

---

**Dimension 2: Ownership and process**

| Signal | Pass | Fail |
|---|---|---|
| Ownership | Treats the code as theirs: "This is mine, I'll make it right." | Hands the problem to the AI |
| Assumption move | On an unclear rule: "I'm assuming X; I'll add a test so that's explicit." | Silently picks a behavior |
| Verifying the map | Opens the functions to confirm what the AI claimed | Takes the AI's summary on faith |
| Debug loop | Spec claim, code seam, hypothesis, test, fix, why it works | Jumps between bugs and patches on hunches |
| Checking in | Runs the approach by you before the first patch and before plan_payouts | Ignores you and only talks to the AI |

---

**Dimension 3: Knowing what the code does**

Use the probing questions in the bug reference and plan_payouts sections.

| Signal | Pass | Fail |
|---|---|---|
| Probing questions | Answers without asking the AI | "The AI changed it" |
| Pushback | "Which algorithm are you choosing? I have something else in mind." | Accepts output they can't explain |

---

**Dimension 4: Prompts**

| Signal | Pass | Fail |
|---|---|---|
| Specificity | Names a rule, a function, or a boundary to check | Open-ended asks like "find all the bugs" |
| Scope | Ends with a constraint like "do not edit files" | Lets the AI pick the scope or rewrite whole sections |

---

**Dimension 5: Narration and simplicity**

| Signal | Pass | Fail |
|---|---|---|
| Narration | Talks while the AI loads: "I expect it to return X" | Sits silently |
| Simplicity | Minimal fixes; plain if/else is fine | Rewrites, abstractions, showing off |
| Money | Integer cents throughout | Floats anywhere in money math |

## plan_payouts guide

The candidate implements this from scratch. As delivered, the body is only `raise NotImplementedError("plan_payouts is not implemented.")`. They should write it only after fixing matching and the snapshot, since payouts depend on both, and they should state their rounding assumption out loud. Expect a check-in with you before they start.

**Expected algorithm:**

1. Count positional matches per entry with `count_matches`
2. Group entries by match count
3. Walk tiers 5, 4, 3, 2
4. Split each tier's amount among its winners with integer division
5. Return awarded and rollover

**Reference implementation:**

```python
def plan_payouts(draw: Draw) -> PayoutPlan:
    by_match = {tier: [] for tier in TIER_PERCENTAGES}
    for entry in draw.entries:
        matches = count_matches(entry.code, draw.winning_code)
        if matches in by_match:
            by_match[matches].append(entry)

    payouts = []
    awarded = 0
    for tier in (5, 4, 3, 2):
        winners = by_match[tier]
        if not winners:
            continue
        category = draw.pot_cents * TIER_PERCENTAGES[tier] // 100
        each = category // len(winners)
        payouts += [Payout(e.id, e.participant, tier, each) for e in winners]
        awarded += each * len(winners)
        if tier == 5:
            break

    return PayoutPlan(tuple(payouts), awarded, draw.pot_cents - awarded)
```

**Probing questions, with expected answers:**

- "What's the impact of `if tier == 5: break`? What if you removed it?" It enforces the rule that a 5-match winner takes everything. Without it, lower tiers get paid too, so awards exceed the pot and rollover goes negative.
- "Why `//` instead of `/`?" `/` produces floats. Money stays in integer cents.
- "Why `draw.pot_cents` instead of the pool's state?" The draw's pot is frozen at close. The pool can change afterward.
- "What does `if matches in by_match` do?" Drops 0- and 1-match entries, since those pay nothing.
- "Where do leftover cents go?" Floor division leaves a remainder, and it lands in rollover.
- "What happens with zero entries?" No payouts, and the whole pot rolls over.

**Tests to expect (given/when/then):**

- Given a pot of 1,002,000 cents with three 4-match entries and one 2-match entry, when payouts are planned, then each 4-match entry gets 133,600, the 2-match entry gets 50,100, and rollover is 551,100.
- Given any entry matching all 5 digits, when payouts are planned, then no lower tier is paid.
- Given a pot of 1,000,000 cents and three 4-match entries, when payouts are planned, then each gets 133,333, and rollover is 600,001 (the untouched 60% plus the 1 leftover cent).
- Given a draw with zero entries, when payouts are planned, then there are no payouts and rollover equals the pot.

**Worked numbers (the spec example):**

| Tier | Tier amount | Winners | Each | Awarded |
|---|---|---|---|---|
| 4 matches (40%) | $4,008.00 | 3 | $1,336.00 | $4,008.00 |
| 2 matches (5%) | $501.00 | 1 | $501.00 | $501.00 |
| Rollover | | | | $5,511.00 |

With no 5-match winner, the tiers sum to at most 65% of the pot, so at least 35% always rolls over.

## Red flags (suggested)

These are built from the workshop's do's and don'ts, grouped for scoring. The grouping is a suggestion, not something the panel gave. Note them during the mock and go through them in the debrief.

**Prompts**

- Uses "fix the problem," "solve it," or "find everything." This is an instant fail in the real round.
- Gives the AI full scope with no constraint, like "review the code and make it correct."
- Accepts AI output without questioning it, even when the AI proposes a full rewrite for a one-line bug.

**Tests**

- Patches a bug before writing a failing test for it.
- Skips boundary cases (00000, 99999, empty draw).
- Tests implementation details instead of behavior from the spec.
- Can't say what a test proves.
- Writes tests that would pass even on the buggy code.

**Code**

- Uses floats anywhere in money math.
- Accepts a rewrite when one line needed to change.
- Adds abstractions the spec didn't ask for.
- Can only explain a fix as "the AI changed it."

**Process**

- Sits silently while the AI loads.
- Starts reading code before clarifying the spec.
- Trusts the AI's map without opening the functions.
- Silently picks a behavior for an unclear rule instead of stating the assumption.
- Drives the AI without ever checking in with you.

## Timing guide (suggested)

The workshop gave 45 minutes total and warned not to let the spec phase eat the interview. The exact spec-phase number was cut off in the recording, so this split is a practice default.

| Phase | Target time | What to watch for |
|---|---|---|
| Read spec + clarifying questions | 5 min | Asks about positional matching, closure, and the snapshot. Uses the assumption move on the deflected question. |
| Map the codebase, then verify | 5 min | Names specific functions, then opens them to check the AI's claims |
| Diagnose bugs | 15 min | One targeted prompt per suspected bug; narrates while the AI loads |
| Patch + test, one bug at a time | 10 min | Failing given/when/then test before each patch; explains each fix |
| Implement plan_payouts | 8 min | Checks in first, states the algorithm and rounding rule out loud |
| Buffer | 2 min | |

**Check-in moments:** expect the candidate to run their approach by you before the first patch and before starting `plan_payouts`. Answer briefly, or redirect.

**Pacing notes:**

- (Suggested) 3 or more bugs fixed with tests by minute 30 is on track.
- The workshop said candidates won't be asked to find every bug, so a clean process on fewer bugs is fine.
- If they're still diagnosing at minute 30 with no tests written: "You have about 15 minutes left. What would you prioritize?"
- (Suggested) If they never asked about positional matching, a fair nudge is: "How does count_matches handle 11111 vs 10101?"
