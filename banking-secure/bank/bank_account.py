# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Bank Account - Lock-Based Approach (Method A)

Assignment Goal: This class directly fulfills the `BankAccount` and `Thread-Safety`
requirements. It demonstrates a classic approach to concurrency control.

- OWASP (Race Conditions): We protect the "critical section" (where the shared
  `_balance` is modified) using an `RLock`. This ensures that only one thread
  can modify the balance at a time, guaranteeing atomicity.
- OWASP (Deadlocks): For the `transfer_to` method, we implement a canonical
  lock ordering strategy. By always acquiring locks in a deterministic order
  (based on account_number), we provably prevent deadlocks.
"""
from decimal import Decimal
from threading import RLock
import time
import bank.config as cfg
from .errors import InsufficientFunds, InvalidAmount

class BankAccount:
    def __init__(self, account_number: str, balance: Decimal):
        self.account_number = account_number
        self._balance = Decimal(balance)
        self._lock = RLock()

    def get_balance(self) -> Decimal:
        with self._lock:
            return Decimal(self._balance)

    def deposit(self, amount: Decimal) -> None:
        amount = Decimal(amount)
        if amount <= 0: raise InvalidAmount("Amount must be positive")
        with self._lock: # Start of critical section
            if cfg.CRIT_DELAY_SEC > 0: time.sleep(cfg.CRIT_DELAY_SEC)
            self._balance += amount

    def withdraw(self, amount: Decimal) -> None:
        amount = Decimal(amount)
        if amount <= 0: raise InvalidAmount("Amount must be positive")
        with self._lock: # Start of critical section
            if self._balance < amount:
                raise InsufficientFunds("Insufficient funds")
            if cfg.CRIT_DELAY_SEC > 0: time.sleep(cfg.CRIT_DELAY_SEC)
            self._balance -= amount

    def transfer_to(self, other: "BankAccount", amount: Decimal) -> None:
        amount = Decimal(amount)
        if self is other: raise ValueError("Cannot transfer to the same account")
        if amount <= 0: raise InvalidAmount("Amount must be positive")

        # DEADLOCK AVOIDANCE STRATEGY (per OWASP guidelines)
        lock1, lock2 = (self._lock, other._lock) if self.account_number < other.account_number else (other._lock, self._lock)
        
        with lock1:
            with lock2:
                # This block is atomic and safe once both locks are held.
                if self._balance < amount:
                    raise InsufficientFunds("Insufficient funds for transfer")
                if cfg.CRIT_DELAY_SEC > 0: time.sleep(cfg.CRIT_DELAY_SEC)
                self._balance -= amount
                other._balance += amount