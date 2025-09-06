# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Bank Account - Lock-Based Approach (Method A)

- Protect critical sections with an RLock (atomicity; no lost updates).
- Use deterministic lock ordering in transfers to prevent deadlocks.
- Validate money amounts centrally via money.py utilities.
"""

from decimal import Decimal
from threading import RLock
import time

import bank.config as cfg
from .errors import InsufficientFunds, InvalidAmount
from .money import validate_amount_positive_in_limits, as_money


class BankAccount:
    def __init__(self, account_number: str, balance: Decimal):
        self.account_number = account_number
        self._balance = as_money(balance)
        self._lock = RLock()

    def __repr__(self) -> str:
        return f"BankAccount({self.account_number}, balance={self._balance})"

    def get_balance(self) -> Decimal:
        with self._lock:
            return as_money(self._balance)

    def deposit(self, amount: Decimal) -> None:
        amt = validate_amount_positive_in_limits(amount)
        with self._lock:
            if cfg.CRIT_DELAY_SEC > 0:
                time.sleep(cfg.CRIT_DELAY_SEC)
            self._balance = as_money(self._balance + amt)

    def withdraw(self, amount: Decimal) -> None:
        amt = validate_amount_positive_in_limits(amount)
        with self._lock:
            if self._balance < amt:
                raise InsufficientFunds("Insufficient funds")
            if cfg.CRIT_DELAY_SEC > 0:
                time.sleep(cfg.CRIT_DELAY_SEC)
            self._balance = as_money(self._balance - amt)

    def transfer_to(self, other: "BankAccount", amount: Decimal) -> None:
        amt = validate_amount_positive_in_limits(amount)
        if self is other:
            raise ValueError("Cannot transfer to the same account")

        # Canonical lock ordering by account_number to avoid deadlocks
        first, second = (self, other) if self.account_number < other.account_number else (other, self)
        with first._lock:
            with second._lock:
                if self._balance < amt:
                    raise InsufficientFunds("Insufficient funds for transfer")
                if cfg.CRIT_DELAY_SEC > 0:
                    time.sleep(cfg.CRIT_DELAY_SEC)
                self._balance = as_money(self._balance - amt)
                other._balance = as_money(other._balance + amt)
