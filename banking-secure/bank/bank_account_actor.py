# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Bank Account - Actor Model (Method B)

Assignment Goal: This class demonstrates a more advanced, alternative solution
to thread safety that aligns with modern distributed system design.

- NIST/OWASP (Secure Design): This architecture *designs out* the possibility of
  race conditions by eliminating shared state. Each actor is a "silo" with its
  own private data and a single thread processing a message queue. This
  serialization of operations per actor inherently guarantees safety.
- Deadlock-Free: As no locks are used, deadlocks are impossible by design.
"""
from decimal import Decimal
from queue import Queue
from threading import Thread
import time
import bank.config as cfg
from .errors import InsufficientFunds, InvalidAmount

class BankAccountActor:
    def __init__(self, account_number: str, balance: Decimal):
        self.account_number = account_number
        self._balance = Decimal(balance)
        self._q: Queue = Queue()
        self._t = Thread(target=self._worker, daemon=True)
        self._t.start()

    def _worker(self):
        """The actor's private worker loop, processes messages sequentially."""
        while True:
            message = self._q.get()
            if message is None: break # Shutdown signal
            op, args, reply_q = message
            try:
                if op == "deposit":
                    amt = Decimal(args["amount"])
                    if amt <= 0: raise InvalidAmount("Amount must be positive")
                    if cfg.CRIT_DELAY_SEC > 0: time.sleep(cfg.CRIT_DELAY_SEC)
                    self._balance += amt
                    reply_q.put(("ok", None))
                elif op == "withdraw":
                    amt = Decimal(args["amount"])
                    if amt <= 0: raise InvalidAmount("Amount must be positive")
                    if self._balance < amt: raise InsufficientFunds("Insufficient funds")
                    if cfg.CRIT_DELAY_SEC > 0: time.sleep(cfg.CRIT_DELAY_SEC)
                    self._balance -= amt
                    reply_q.put(("ok", None))
                elif op == "balance":
                    reply_q.put(("ok", Decimal(self._balance)))
                else:
                    reply_q.put(("err", ValueError("Unknown operation")))
            except Exception as e:
                reply_q.put(("err", e))

    def _call(self, op: str, **kwargs):
        """Helper to send a message and block for a reply."""
        reply = Queue()
        self._q.put((op, kwargs, reply))
        status, payload = reply.get()
        if status == "ok": return payload
        raise payload

    def get_balance(self) -> Decimal: return self._call("balance")
    def deposit(self, amount: Decimal) -> None: self._call("deposit", amount=amount)
    def withdraw(self, amount: Decimal) -> None: self._call("withdraw", amount=amount)
    def stop(self) -> None: self._q.put(None)

    def transfer_to(self, other: "BankAccountActor", amount: Decimal) -> None:
        amount = Decimal(amount)
        if self is other: raise ValueError("Cannot transfer to the same account")
        if amount <= 0: raise InvalidAmount("Amount must be positive")
        
        # This is a compensation-based transaction (Saga pattern).
        self.withdraw(amount)
        try:
            other.deposit(amount)
        except Exception as e:
            self.deposit(amount) # Compensate on failure (refund).
            raise e

def warn_many_actors(n: int):
    if n >= cfg.ACTOR_THREAD_WARN_THRESHOLD:
        print(f"[WARN] Creating {n} actor accounts => {n} threads. This may be resource-intensive.")