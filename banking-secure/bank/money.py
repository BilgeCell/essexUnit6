# ==========================
# File: bank/money.py
# ==========================
# -*- coding: utf-8 -*-
"""
Secure Money Handling Utilities.

Purpose:
- Enforces that all monetary values are handled with `Decimal`, not float,
  to avoid floating-point rounding errors in financial calculations.
- Centralizes business rules: uses MIN_TRANSACTION and MAX_TRANSACTION from config.
- Provides helper functions to normalize and validate amounts before use.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from .config import MIN_TRANSACTION, MAX_TRANSACTION
from .errors import InvalidAmount


def as_money(value) -> Decimal:
    """
    Normalize any input to Decimal with 2 fractional digits.

    Why:
    - Guarantees consistent 2dp (e.g., "10.00") across the system.
    - Avoids subtle float inaccuracies (e.g., 0.1 + 0.2 != 0.3).
    """
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def validate_amount_positive_in_limits(amount) -> Decimal:
    """
    Validate that the amount is within allowed limits and return normalized Decimal.

    Rules:
    - Must be >= MIN_TRANSACTION (e.g., 0.01).
    - Must be <= MAX_TRANSACTION (business maximum).
    - Raises InvalidAmount if validation fails.
    """
    amt = as_money(amount)
    if amt < as_money(MIN_TRANSACTION):
        raise InvalidAmount(f"Amount must be >= {MIN_TRANSACTION}")
    if amt > as_money(MAX_TRANSACTION):
        raise InvalidAmount(f"Amount must be <= {MAX_TRANSACTION}")
    return amt
