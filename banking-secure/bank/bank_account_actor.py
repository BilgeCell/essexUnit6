# -*- coding: utf-8 -*-
from __future__ import annotations
from decimal import Decimal
from queue import Queue, Empty
from threading import Thread
import time
import bank.config as cfg
from .errors import InsufficientFunds, InvalidAmount
from .money import validate_amount_positive_in_limits, as_money
"""
Bank Account - Actor Model (Method B)

Goal: This class demonstrates a more advanced, alternative solution
to thread safety that aligns with modern distributed system design.

- NIST/OWASP (Secure Design): This architecture *designs out* the possibility of
  race conditions by eliminating shared state. Each actor is a "silo" with its
  own private data and a single thread processing a message queue. This
  serialization of operations per actor inherently guarantees safety.
- Deadlock-Free: As no locks are used, deadlocks are impossible by design.
"""

"""
Bank Account - Actor Model (Method B)

- Single-threaded actor per account; eliminates shared-state races by design.
- No locks; deadlocks are impossible inside a single actor.
- Amount validation uses centralized money utilities.
- Blocking calls have a timeout to avoid hangs.
"""



class BankAccountActor:
    def __init__(self, account_number: str, balance: Decimal):
        self.account_number = account_number
        self._balance = as_money(balance)
        self._q: Queue = Queue()
        self._t = Thread(target=self._worker, daemon=True)
        self._running = True
        self._t.start()

    # -------- internal worker --------
    def _worker(self):
        while True:
            message = self._q.get()
            if message is None:  # shutdown
                break
            op, args, reply_q = message
            try:
                if op == "deposit":
                    amt = validate_amount_positive_in_limits(args["amount"])
                    if cfg.CRIT_DELAY_SEC > 0:
                        time.sleep(cfg.CRIT_DELAY_SEC)
                    self._balance = as_money(self._balance + amt)
                    reply_q.put(("ok", None))
                elif op == "withdraw":
                    amt = validate_amount_positive_in_limits(args["amount"])
                    if self._balance < amt:
                        raise InsufficientFunds("Insufficient funds")
                    if cfg.CRIT_DELAY_SEC > 0:
                        time.sleep(cfg.CRIT_DELAY_SEC)
                    self._balance = as_money(self._balance - amt)
                    reply_q.put(("ok", None))
                elif op == "balance":
                    reply_q.put(("ok", as_money(self._balance)))
                else:
                    reply_q.put(("err", ValueError("Unknown operation")))
            except Exception as e:
                reply_q.put(("err", e))

    # -------- sync call helper --------
    def _call(self, op: str, **kwargs):
        reply: Queue = Queue()
        self._q.put((op, kwargs, reply))
        try:
            status, payload = reply.get(timeout=cfg.ACTOR_CALL_TIMEOUT_SEC)
        except Empty:
            raise TimeoutError(f"Actor call timed out for op={op}")
        if status == "ok":
            return payload
        raise payload

    # -------- public API --------
    def get_balance(self) -> Decimal:
        return self._call("balance")

    def deposit(self, amount: Decimal) -> None:
        self._call("deposit", amount=amount)

    def withdraw(self, amount: Decimal) -> None:
        self._call("withdraw", amount=amount)

    def stop(self) -> None:
        if self._running:
            self._running = False
            self._q.put(None)
            self._t.join(timeout=cfg.ACTOR_CALL_TIMEOUT_SEC)

    def transfer_to(self, other: "BankAccountActor", amount: Decimal) -> None:
        amt = validate_amount_positive_in_limits(amount)
        if self is other:
            raise ValueError("Cannot transfer to the same account")
        # Saga-style compensation: withdraw then deposit; refund if deposit fails
        self.withdraw(amt)
        try:
            other.deposit(amt)
        except Exception as e:
            # compensate
            self.deposit(amt)
            raise e


def warn_many_actors(n: int):
    if n >= cfg.ACTOR_THREAD_WARN_THRESHOLD:
        print(f"[WARN] Creating {n} actor accounts => {n} threads. This may be resource-intensive.")
