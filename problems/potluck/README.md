# Pot Luck

## Requirements

- Python 3.9+
- pytest

## Setup

```bash
pip install pytest
```

No other dependencies. All code uses the standard library plus pytest.

## Files

| File | Purpose |
|------|---------|
| `spec.md` | Problem specification |
| `question.py` | Implementation |
| `test_potluck_shipped.py` | Pre-shipped tests |
| `test_potluck.py` | Your tests |
| `conftest.py` | Shared pytest fixtures: `fresh_pool`, `make_pool`, `make_draw` |
| `sample_run.py` | Demo script |

## Running tests

```bash
# Shipped suite: 13 pass, and the 4 payout tests fail until plan_payouts is implemented
pytest test_potluck_shipped.py -v

# Your tests
pytest test_potluck.py -v

# Everything
pytest -v

# Stop on the first failure
pytest test_potluck.py -x -v
```

## Demo

```bash
python3 sample_run.py
```

## Fixtures

```python
def test_example(fresh_pool):
    entry = fresh_pool.enter("Alice")

def test_example(make_pool):
    pool = make_pool(lambda: 0.5)

def test_example(make_draw):
    draw = make_draw("12345", 1_002_000, [("Alice", "12345"), ("Bob", "67890")])
```
