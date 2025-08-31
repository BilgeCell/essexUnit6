# -*- coding: utf-8 -*-
"""
Secure Money Handling Utilities.

Philosophy: Following OWASP guidelines on data validation, this module ensures
financial data integrity. It enforces that money is always represented by the
`Decimal` type to prevent floating-point errors and validates all transaction
amounts against centrally-defined business rules.
"""
from decimal import Decimal
from .config import MIN_TRANSACTION, MAX_TRANSACTION
from .errors import InvalidAmount

def as_money(value: any) -> Decimal:
    """Normalizes any input to a Decimal with 2 fractional digits."""
    return Decimal(str(value)).quantize(Decimal("0.01"))

def validate_amount_positive_in_limits(amount: any) -> Decimal:
    """Validates that the amount is positive and within business limits."""
    amt = as_money(amount)
    if amt < as_money(MIN_TRANSACTION):
        raise InvalidAmount(f"Amount must be >= {MIN_TRANSACTION}")
    if amt > as_money(MAX_TRANSACTION):
        raise InvalidAmount(f"Amount must be <= {MAX_TRANSACTION}")
    return amt