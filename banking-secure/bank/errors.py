# -*- coding: utf-8 -*-
"""
Custom Exception Classes.

Philosophy: Defining specific exceptions makes a program's behavior more
predictable and secure. Instead of raising a generic error, custom types like
`InsufficientFunds` allow calling code to handle specific business rule
failures gracefully and correctly.
"""

class InsufficientFunds(Exception):
    """Raised when an operation cannot be completed due to lack of funds."""
    pass

class InvalidAmount(Exception):
    """Raised for invalid transaction amounts (e.g., negative or zero)."""
    pass