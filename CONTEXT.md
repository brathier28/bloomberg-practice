# Bloomberg Tech-AI Practice: Generator Context

This file teaches Claude Code how to build practice problems for Bloomberg's
new-grad Tech-AI interview round, plus a matching answer key for a mock
interviewer. Read the whole file before generating anything.

Pot Luck (Appendix A) is the reference problem. Every new problem should match
its structure, difficulty, and level of subtlety.

Anything marked **(suggested)** is a practice default, not something the
Bloomberg workshop said. Everything else comes from the workshop notes.

---

## 0. Folder layout (read this first)

This file contains answers. The AI agent used during a timed run must never
see it, or any answer key.

```
bloomberg-practice/
  CONTEXT.md                 <- this file (generator brain, contains answers)
  answer-keys/
    potluck.md               <- interviewer cheat sheet, one per problem
    <problem>.md
  problems/
    potluck/                 <- candidate-facing files only
    <problem>/
```

Rules:

- Do not rename this file to `CLAUDE.md`. Claude Code loads `CLAUDE.md` files
  automatically from the launch folder and its parents, which would leak
  answers into a practice session.
- During a timed run, launch the AI agent inside `problems/<problem>/` only.
- Nothing under `problems/` may contain answers, hints, fixed code, or
  comments that point at bugs. This includes test names (see section 2).

---

## 1. What the real round looks like

From a Bloomberg workshop on the new format (fall 2026):

- The loop has 5 rounds: 2 Tech-AI rounds (45 minutes each, HackerRank with an
  embedded Claude agent), 1 system design round, HR, and a manager round.
- Tech-AI round: one tiered question. The candidate gets a spec and a
  partially built codebase with planted bugs. They direct the AI to
  understand the code, find and fix bugs, and implement one unfinished
  function.
- The candidate won't be asked to find every bug, and the bugs are meant to
  be clear. The interviewer may point them at an area.
- The two Tech-AI rounds are similar in format but draw from different
  question pools.

### What is graded

The grade is how the candidate directs the AI, not whether they find the
answer. In the panel's order:

1. **Tests are the strongest signal.** Called the most important part more
   than once. A failing test before every patch, boundary conditions first,
   and every test written as behavior from the spec (BDD, section 1a).
2. **Ownership.** Treat it like your own product, not "AI, my PM said X."
3. **A systematic process** that keeps the AI from dragging you off scope.
4. **Knowing what your code does.** Expect "what's the impact of this line?"
   and "what happens if you did X instead?" (section 6, probing questions).

Also expected:

- **Prompts with a goal and a boundary** ("do not edit files", "do not patch
  anything"). "Fix the problem", "solve it", and "find everything" are
  instant fails.
- **Narration** while the AI loads: "I expect it to return X."
- **Simplicity.** Small patches. If/else is fine. Don't show off. Money is
  integer cents, never floats.

### The candidate's 6-step workflow

Read spec, clarify gaps, map code, diagnose bugs, patch small, validate.
Then implement the unfinished function.

### 1a. BDD (flagged IMPORTANT**** at the workshop)

Behavior-driven development means writing tests that describe what the
system should do according to the spec, not how the code implements it.

Format: **given** some starting state, **when** an action happens, **then**
expect an outcome.

Example: given a closed draw, when someone calls `enter()`, then it raises
`FundraiserError` and the pot is unchanged.

Why it matters in this round: the AI writes the code. A test written against
the implementation ("check that `self._draw` is not None") can pass even when
behavior is wrong. A test written against the spec catches the bug however
the AI implemented it.

It shows up in two places:

- **Test names** that state the spec guarantee, e.g.
  `test_closed_draw_rejects_new_entry_and_leaves_pot_unchanged`.
- **Narration.** Saying the test out loud in given/when/then form tells the
  interviewer you're testing the spec.

### 1b. Habits the interviewer looks for

- **The assumption move.** When a gap can't be clarified: "I'm assuming X;
  I'll add a test so that assumption is explicit."
- **Verify the AI's map.** "AI is a map, the repository is the territory."
  After the AI points to functions, open them and check its claims.
- **The debug loop, per bug.** Spec claim, then code seam, then hypothesis,
  then a failing test, then a minimal fix, then explain why the test proves
  it.
- **Check in with the interviewer.** "I'm going to do this approach, what do
  you think?" Don't ignore the interviewer in favor of the AI.

---

## 2. Anatomy of a practice problem

Each problem in `problems/<name>/` has exactly these files:

| File | Contents |
|---|---|
| `spec.md` | Clean spec written as if from Bloomberg. Overview, rules by area, one worked numeric example, data model table, required interface. No hints. |
| `question.py` | Working implementation with exactly 5 planted bugs. The target function keeps its signature and docstring; its body is only `raise NotImplementedError("<name> is not implemented.")` |
| `test_<name>_shipped.py` | Shallow tests that pass against the buggy code by avoiding sharp edges. Tests for the target function fail with NotImplementedError. That is expected. |
| `test_<name>.py` | Candidate's test file. **Default:** imports plus one comment, `# Add your tests here.` No test names. See "Training wheels" below. |
| `conftest.py` | Fixtures: a fresh instance, a factory with an injectable random/clock source, and a factory that builds the target function's input directly from known values. Docstring examples follow "Hint hygiene" below. |
| `sample_run.py` | Happy-path demo with a fixed seed. Must not reveal any bug in its output. |
| `README.md` | Setup only: requirements, install command, file table, and pytest commands. Shipped-test counts must match reality (for example, 13 pass / 4 fail). No workflow advice and no example inputs or outputs. See "Hint hygiene" below. |
| `pyproject.toml` | pytest config. Python 3.9+, standard library plus pytest only. |

### Training wheels (opt-in only)

Generate a named test skeleton only if the user explicitly asks for training
wheels. A named skeleton gives away bugs (a name like
`test_random_source_near_one_produces_upper_boundary_code` points straight at
Bug 1), and writing the names in given/when/then form is itself the BDD
practice. When requested, use BDD-style names with `pass` bodies.

### Hint hygiene

Everything in `problems/<name>/` is visible to the candidate and to the AI
agent, so it must not hint at any bug. In particular:

- **No expected outputs in examples.** Docstrings, README snippets, and
  comments may show how to call something, but never what it should return.
  Bad: `make_pool(lambda: 0.0)` followed by `assert entry.code == "00000"`.
  Good: `make_pool(lambda: 0.5)` followed by `entry = pool.enter("Alice")`.
- **No boundary values in examples.** Use neutral inputs like 0.5. Avoid
  0.0, 0.99999, empty inputs, or any value an exposing test would use.
- **No comments that label inputs.** Bad: `lambda: 0.99999  # upper boundary`.
- **No process coaching.** The README doesn't tell the candidate to write
  failing tests first, read the spec first, or inspect output carefully.
  That process is what the round grades.
- **Exception:** `spec.md` may include its one worked numeric example, since
  the real spec does.

Check every candidate-facing file against this list before reporting back.

### Conventions

- **Dependency injection for randomness and time.** Any random or time-based
  value comes from an injectable callable, so boundary tests need no
  monkey-patching.
- **Frozen dataclasses** for records.
- **Integer cents** for every money value.
- **Docstrings that describe the intended behavior**, including for buggy
  functions. The docstring states the rule correctly and the code violates
  it. This lets a candidate catch bugs by comparing spec, docstring, and code.
- **BDD test names** in answer keys and in any opt-in skeleton.

---

## 3. Bug design rules

Plant exactly 5 bugs, one per category. Every bug must:

- Violate one specific spec line (the "spec claim" in the debug loop).
- Pass the happy path. The shipped tests must stay green on it.
- Be exposable by one small, specific input, stated as a given/when/then.
- Have a minimal fix of one to three lines.
- Have no comment, odd naming, or formatting quirk near it.

| # | Category | Pot Luck instance | Generalizes to |
|---|---|---|---|
| 1 | Boundary / off-by-one | `* 99_999` makes 99999 unreachable | range endpoints, `<` vs `<=`, inclusive limits, last element |
| 2 | Representation / format | `str(42)` loses leading zeros | padding, int vs float, rounding mode, timezone, string vs number keys |
| 3 | Wrong semantics that pass the happy path | set intersection instead of positional matching | set vs multiset, order sensitivity, dedupe, first vs all matches |
| 4 | Missing state guard | `enter()` accepts entries after close | lifecycle checks, double-submit, cancel after settle, mutation after lock |
| 5 | Aliasing / mutable reference | Draw stores the live list | stored references, shared default args, shallow copies |

**Dependency chain.** The target function must depend on at least two bugs
being fixed (Pot Luck's `plan_payouts` depends on matching and the snapshot),
so a correct implementation still produces wrong numbers until those bugs are
fixed.

**Shipped tests hide the bugs on purpose.** Pick inputs that dodge each bug.
Example: Pot Luck's shipped matching tests use `"12345"` (all unique digits)
so set intersection happens to give the right answer.

---

## 4. Spec design rules

- Every spec line should imply code and a test.
- Include one worked numeric example that a correct target function
  reproduces exactly.
- Leave 2 or 3 things deliberately unspecified for the candidate to clarify,
  such as remainder handling, multiplicity (one person, many entries), or
  capacity limits. At least one of these should be one the mock interviewer
  deflects ("your call"), so the candidate has to use the assumption move.
- Keep it backend-only, about one page.

### Domain bank (suggested)

- Order book matching with price-time priority
- Trade settlement netting between counterparties
- Portfolio rebalancing to target weights, in cents
- FX conversion with rounding and fee tiers
- Bond coupon schedule generation
- Market-data feed dedupe and sequencing
- Rate limiter with per-client quotas
- Expense splitting with remainder rules

---

## 5. Generation checklist (follow in order)

When asked to generate a new problem:

1. **Pick the domain** (from the request or the domain bank) and write
   `spec.md`.
2. **Write a correct reference implementation first**, privately. Then plant
   the 5 bugs, one per category, to produce `question.py`. Replace the target
   function's body with the NotImplementedError stub.
3. **Verify every bug**, using a scratch file outside `problems/`:
   - For each bug, write the exposing test with a BDD name. Confirm it fails
     on the buggy code and passes on the reference implementation.
   - Confirm the worked example from `spec.md` reproduces exactly on the
     reference implementation.
   - Confirm `test_<name>_shipped.py` passes on the buggy code, except
     target-function tests, which fail with NotImplementedError. Record the
     exact pass/fail counts.
   - Confirm `test_<name>.py` imports cleanly.
   - Check every candidate-facing file against "Hint hygiene" (section 2).
4. **Delete the scratch files.** The reference implementation and the
   exposing tests go into the answer key only.
5. **Record final line numbers** for each bug from the finished
   `question.py`.
6. **Write `answer-keys/<name>.md`** using the template in section 6.
7. **Report back with only:** the file list and test-run counts. Do not
   summarize the bugs in chat. The user may be the candidate.

---

## 6. Answer key template

Write `answer-keys/<name>.md` with these sections, in this order. Use plain
markdown (headings, tables, fenced code) so it pastes cleanly into Google Docs
or a Claude Doc. Label anything not from the workshop as "(suggested)".

1. **Spec to hand the candidate.** The spec verbatim, plus a one-line answer
   for when they ask what the target function does.
2. **Clarifying questions to expect.** Table: question / answer to give, or
   "deflect: your call" / bug it surfaces (or "neutral"). Mark at least one
   question to deflect, and note that the candidate should respond with the
   assumption move. End with a scoring note on which questions matter most.
3. **Codebase overview.** File table, the key fixture, and the starting-state
   commands with exact expected pass/fail counts.
4. **Verify the map.** Two to four yes/no questions the candidate should
   check in the code after the AI maps it. The mock interviewer can ask "how
   do you know that's true?"
5. **Bug reference.** For each bug, in debug-loop order:
   - Spec claim (the spec line it violates)
   - Code seam (function, line number, and the buggy line)
   - Hypothesis (one sentence)
   - Failing test as given/when/then, with the exact input
   - A good prompt that would surface it
   - Minimal fix
   - Why the test proves the fix
   - Probing questions with expected answers
6. **Grading rubric.** Pass/fail tables, in this order: tests (including BDD
   phrasing), ownership and process (including the assumption move, verifying
   the map, the debug loop, and checking in with the interviewer), knowing
   what the code does, prompts, narration, simplicity. State the instant-fail
   rule. Tests come first because the panel called them the strongest signal.
7. **Target function guide.** The algorithm in steps, the reference
   implementation, probing questions about specific lines with expected
   answers, and the worked numbers as a table.
8. **Red flags (suggested).** Grouped as prompt, testing, code, and process.
9. **Timing guide (suggested).** Table below, plus check-in moments and fair
   nudges.

### Timing (suggested)

The workshop gave 45 minutes total and said not to let the spec phase eat the
interview. The exact spec-phase number was cut off in the recording, so this
split is a practice default.

| Phase | Target |
|---|---|
| Read spec + clarifying questions | 5 min |
| Map the codebase via the AI, then verify | 5 min |
| Diagnose bugs with targeted prompts | 15 min |
| Patch + test, one bug at a time | 10 min |
| Implement the target function | 8 min |
| Buffer | 2 min |

Expected check-ins with the interviewer: before the first patch, and before
starting the target function.

Pacing (suggested): 3 or more bugs fixed with tests by minute 30 is on track.
The workshop said candidates won't be asked to find every bug, so a clean
process on fewer bugs is fine.

---

## 7. Prompt bank (for evaluating the candidate)

Good prompts end with a constraint. Use these as the benchmark in the answer
key's "good prompt" fields.

- Spec: "Read spec.md. Only summarize the rules as a checklist. Then list
  assumptions I should clarify before I inspect the code."
- Map: "In question.py, point me to the functions responsible for X, Y, Z.
  Symbol name and a one-line description each. Do not edit files."
- Challenge: "Compare question.py against these rules: <rules>. List up to
  five likely violations. For each, give the smallest input that would expose
  it. Do not patch anything."
- Targeted: "I want <range>. Are there gaps? Add a test that verifies the
  upper boundary."
- Stress: "Do X, close/lock, then do X 100,000 more times. Verify none are
  counted."
- Before implementing: "Given the spec, list the edge cases and assumptions I
  should validate with tests."
- Pushback: "Which algorithm are you choosing? I have something else in mind."

---

## 8. Still unknown about the real round

The workshop audio was unclear on these. Don't build problems that depend on
the answers.

- Exact time limit for the spec phase
- Which rounds happen in person during the campus visit
- Whether the manager round includes its own design question
- How Tech-AI round 1 differs from round 2

---

## Appendix A: Pot Luck (reference problem)

Location: `problems/potluck/`. Answer key: `answer-keys/potluck.md`.

**Spec summary.** $10,000 sponsor seed plus $5 per entry, computed at draw
time. 5-digit codes 00000 to 99999 inclusive. Tiers: 5 matches 100%, 4 = 40%,
3 = 20%, 2 = 5%. Processed 5 down to 2. A 5-match winner takes the whole pot
and lower tiers get nothing. Same-tier winners split equally in integer
cents. Everything unawarded rolls over.

**Clarifying question to deflect:** multiplicity (can one participant win
with multiple entries?). Answer "your call" and look for the assumption move.

**Spec discrepancy to know:** the workshop said the same code is never given
to two people, which makes "more than 100,000 entries" a real capacity gap.
The Pot Luck `spec.md` instead says duplicates are possible, which removes
that gap. Pick one before a mock and tell the interviewer which.

**Verify the map:**
- Does the random range preserve both 00000 and 99999?
- Does the closed draw hold a copied snapshot of the entries?
- Does payout code read the frozen pot from the draw?

**Bugs (debug-loop order):**

| # | Spec claim | Code seam | Given / when / then | Fix |
|---|---|---|---|---|
| 1 | Codes run 00000 to 99999 inclusive | `_generate_code`, line 122: `int(self._random_source() * 99_999)` | Given a random source returning 0.999999, when an entry is created, then its code is "99999" (buggy: 99998) | multiply by `100_000` |
| 2 | Codes are five digits, leading zeros kept | `_generate_code`, line 123: `return str(number)` | Given a random source returning 0.000425 (yields 42), when an entry is created, then its code is "00042" (buggy: "42") | `f"{number:05d}"` |
| 3 | Matches are positional, no dedupe | `count_matches`, line 212: `len(set(entry_code) & set(winning_code))` | Given entry 11111 and winning code 10101, when matches are counted, then the result is 3 (buggy: 1). Also 12345 vs 54321 = 1, 00000 vs 00000 = 5 | positional `zip` plus a length check |
| 4 | No entries after the draw closes | `enter`, lines 148-151: no guard before `uuid.uuid4()` | Given a closed draw, when someone enters, then `FundraiserError` is raised and the draw's entries and pot are unchanged | raise first if `self._draw is not None` |
| 5 | A closed draw is a frozen snapshot | `close_draw`, line 180: `entries=self._entries` | Given a closed draw, when the pool's entry list is appended to, then `draw.entries` is unchanged | `entries=tuple(self._entries)` |

**Probing questions, with expected answers:**

- Bug 1: "Why 100,000 and not 99,999?" `random_source()` returns values in
  [0, 1), never 1, so `* 99_999` tops out at 99,998. `* 100_000` covers 0 to
  99,999.
- Bug 2: "What does the winning code look like when the random value is 0?"
  "0" instead of "00000", so it can never match five positions.
- Bug 3: "Why the length check?" `zip` stops silently at the shorter string,
  so a 4-character code would undercount with no error.
- Bug 4: "Why does the guard go first?" Otherwise a rejected entry still gets
  an id, a code, and is appended to the pool's list. With Bug 5 unfixed, it
  would even leak into the closed draw.
- Bug 5: "Why `tuple(...)` instead of `list(self._entries)`?" Both copy, but a
  list can still be mutated later. `frozen=True` on the dataclass only stops
  reassigning the field, not mutating a list inside it. A tuple also matches
  the `Tuple[Entry, ...]` type hint.

**Target function:** `plan_payouts(draw) -> PayoutPlan`.

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

**Probing questions on `plan_payouts`:**

- "What's the impact of `if tier == 5: break`? What if you removed it?" It
  enforces the override rule. Without it, a 5-match winner gets 100% and the
  lower tiers are paid too, so awards exceed the pot and rollover goes
  negative.
- "Why `//` instead of `/`?" `/` produces floats. Money stays in integer
  cents.
- "Why `draw.pot_cents` instead of the pool?" The draw's pot is frozen at
  close. The pool's state can change afterward.
- "What does `if matches in by_match` do?" Drops 0- and 1-match entries,
  since those tiers pay nothing.
- "Where do leftover cents go?" Floor division leaves a remainder, which
  lands in rollover.
- "What happens with zero entries?" No payouts, and the full pot rolls over.

**Worked example and BDD tests for `plan_payouts`:**

- Given a pot of 1,002,000 cents with three 4-match entries and one 2-match
  entry, when payouts are planned, then each 4-match entry gets 133,600, the
  2-match entry gets 50,100, and rollover is 551,100.
- Given any entry matching all 5 digits, when payouts are planned, then no
  lower tier is paid.
- Given a pot of 1,000,000 cents and three 4-match entries, when payouts are
  planned, then each gets 133,333, and rollover is 600,001 (the untouched
  60% plus the 1 leftover cent).
- Given a draw with zero entries, when payouts are planned, then there are no
  payouts and rollover equals the pot.

**Shipped test counts:** 17 tests in `test_potluck_shipped.py`. With
`plan_payouts` stubbed, 13 pass and the 4 in `TestShippedPayoutPlan` fail
with NotImplementedError.

**Known fixes needed in `problems/potluck/`:**
- `README.md` says the shipped tests "all pass as delivered." Update it to
  the counts above.
- `README.md` breaks hint hygiene: the dependency-injection section labels
  `0.99999` as the upper boundary and says `0.0` gives `"00000"`, and the
  Workflow section coaches the graded process. Keep only Requirements,
  Setup, Files, and Running tests. If the fixtures section stays, remove the
  comments after each example.
- `conftest.py`: the `make_pool` docstring asserts `entry.code == "00000"`.
  Replace the example with `pool = make_pool(lambda: 0.5)` and
  `entry = pool.enter("Alice")`, with no assertion.
- `test_potluck.py` is a named skeleton whose names give away the bugs.
  Replace it with the default empty file unless training wheels are wanted.
