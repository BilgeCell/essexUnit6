# -*- coding: utf-8 -*-
"""
Package for the core logic of the secure and concurrent banking system.

Philosophy: This __init__ file sets the global `Decimal` context to ensure
data integrity and accuracy in all financial calculations. This is a
cornerstone of secure, reliable financial software, directly addressing the
need for precision in financial systems.
"""
from decimal import getcontext, ROUND_HALF_EVEN

# Set the global context for Decimal operations for financial accuracy.
# Banker's rounding is used as it minimizes statistical bias.
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_EVEN