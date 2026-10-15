"""Your test file. Add tests here."""

import pytest
from datetime import date

from question import (
    BookError,
    Trade,
    TradeBook,
    NetObligation,
    NettingRun,
    _build_obligation,
    _is_in_scope,
    _net_signed,
    net_obligations,
)

# Add your tests here.
