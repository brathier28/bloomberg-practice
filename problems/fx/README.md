# FX Desk — Daily Settlement

## Requirements

Python 3.9 or later, plus pytest.

## Setup

```
pip install pytest
```

## Files

| File | Description |
|------|-------------|
| `spec.md` | Problem specification |
| `question.py` | Implementation to work with |
| `conftest.py` | Shared fixtures |
| `test_fx_shipped.py` | Shipped tests |
| `test_fx.py` | Your test file |
| `sample_run.py` | Happy-path demo |
| `pyproject.toml` | pytest configuration |

## Running tests

Shipped tests:

```
pytest test_fx_shipped.py -v
```

Your tests:

```
pytest test_fx.py -v
```

All tests:

```
pytest -v
```

Shipped test counts: 14 pass / 4 fail with NotImplementedError.
