# Trade Settlement Netting

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
| `test_netting_shipped.py` | Pre-shipped tests |
| `test_netting.py` | Your tests |
| `conftest.py` | Shared pytest fixtures: `fresh_book`, `make_book`, `make_trade_group` |
| `sample_run.py` | Demo script |

## Running tests

```bash
# Shipped suite: 13 pass, and the 4 netting-run tests fail until net_obligations is implemented
pytest test_netting_shipped.py -v

# Your tests
pytest test_netting.py -v

# Everything
pytest -v

# Stop on the first failure
pytest test_netting.py -x -v
```

## Demo

```bash
python3 sample_run.py
```

## Fixtures

```python
def test_example(fresh_book):
    fresh_book.add_trade("ALPHA", "USD", "buy", 500_000, date(2026, 10, 15))

def test_example(make_book):
    book = make_book()

def test_example(make_trade_group):
    trades = make_trade_group("ALPHA", "USD", date(2026, 10, 15), buys=[500_000])
```
