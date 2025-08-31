# -*- coding: utf-8 -*-
"""
Central Configuration File.

Philosophy: This file follows the "Single Source of Truth" (SSOT) principle.
All business rules (e.g., currency, transaction limits) and simulation
parameters are centralized here. This improves maintainability and security, as
critical values are managed in one predictable location.
"""

# --- Business Rules ---
CURRENCY = "GBP"
CURRENCY_SYMBOLS = {
    "GBP": "£",
    "TRY": "₺",
    "USD": "$",
    "EUR": "€",
}
MIN_TRANSACTION = "0.01"
MAX_TRANSACTION = "1000000.00"

# --- Simulation Settings ---
# This artificial delay is a pedagogical tool. It enlarges the critical section
# to make the effects of contention more visible and measurable.
CRIT_DELAY_SEC: float = 0.001

# A simple warning threshold for creating a large number of actor threads.
ACTOR_THREAD_WARN_THRESHOLD: int = 300