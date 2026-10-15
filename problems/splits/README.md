# Tab Split — Group Expense Splitter

## Requirements

Python 3.9 or later. Standard library plus pytest.

## Setup

```shell
pip install pytest
```

## Files

| File | Purpose |
|------|---------|
| `spec.md` | Full specification |
| `question.py` | Implementation |
| `conftest.py` | Pytest fixtures |
| `test_splits_shipped.py` | Pre-shipped tests |
| `test_splits.py` | Your test file |
| `sample_run.py` | Happy-path demonstration |
| `pyproject.toml` | Pytest configuration |

## Running tests

```shell
# Shipped tests only
pytest test_splits_shipped.py -v

# Your tests only
pytest test_splits.py -v

# Everything
pytest -v
```

As delivered: 12 pass, 4 fail with `NotImplementedError`.
