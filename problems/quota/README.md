# Quota

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
| `test_quota_shipped.py` | Pre-shipped tests |
| `test_quota.py` | Your tests |
| `conftest.py` | Shared pytest fixtures: `fresh_limiter`, `make_limiter`, `make_batch` |
| `sample_run.py` | Demo script |

## Running tests

```bash
# Shipped suite: 15 pass, and the 4 bill tests fail until compute_bill is implemented
pytest test_quota_shipped.py -v

# Your tests
pytest test_quota.py -v

# Everything
pytest -v

# Stop on the first failure
pytest test_quota.py -x -v
```

## Demo

```bash
python3 sample_run.py
```
