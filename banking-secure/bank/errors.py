# -*- coding: utf-8 -*-
"""
Custom Exception Classes for Banking Domain.

Purpose:
- Provide clear, domain-specific errors for banking operations.
- Enable calling code (tests, simulators, CLI) to handle business rule
  violations gracefully, instead of catching generic Exception.
- Following secure coding best practices, explicit exceptions reduce ambiguity
  and improve system robustness.
"""


class InsufficientFunds(Exception):
    """
    Raised when a withdrawal or transfer cannot be completed because
    the account balance is insufficient.
    """
    pass


class InvalidAmount(Exception):
    """
    Raised when a transaction amount is invalid:
    - Negative or zero value.
    - Outside the configured business rules (min/max transaction limits).
    """
    pass
