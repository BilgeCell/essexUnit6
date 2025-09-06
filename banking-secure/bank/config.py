"""
Central Configuration File (SSOT).
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
CRIT_DELAY_SEC: float = 0.001  # pedagogical critical-section delay

# Actor warnings / timeouts
ACTOR_THREAD_WARN_THRESHOLD: int = 300
ACTOR_CALL_TIMEOUT_SEC: float = 5.0  # to avoid hanging calls


