# -*- coding: utf-8 -*-
from __future__ import annotations

import random
import time
from decimal import Decimal, ROUND_HALF_EVEN
from threading import Thread, Lock
from typing import Dict, List, Tuple

from .money import as_money
from .errors import InsufficientFunds, InvalidAmount

"""
Concurrent Transaction Simulator

Goal:
- This module empirically validates the thread safety of different bank account models.
- It creates concurrent workloads and measures whether correctness invariants hold.
- Key proof: In a closed transfer-only economy, total drift must be 0.00.
"""

# ==========================
# File: bank/transaction_simulator.py
# ==========================
"""
TransactionSimulator — enriched metrics (whitepaper-ready)

Purpose:
- Drive concurrent workloads over a list of accounts (lock-based or actor-based).
- Produce auditable metrics for correctness and performance.

Collected metrics:
- attempted.total / succeeded.total / failed.total
- failed.by_reason: {insufficient_funds, invalid_amount, same_account, other}
- avg_latency_ms, p95_latency_ms (per-operation wall-clock latency)
- ops_per_sec (throughput under load)
- total_drift (Decimal, 2dp) — must be £0.00 in transfer-only scenarios.

Notes:
- Python threads are used; GIL limits CPU parallelism but suffices for
  demonstrating race conditions and actor serialization.
- Amount ranges and precision come from money.py.
"""


class TransactionSimulator:
    """
    TransactionSimulator runs concurrent operations (deposit, withdraw, transfer)
    on a given set of accounts.

    Academic purpose:
    - Empirically validate concurrency safety of BankAccount (lock-based) and
      BankAccountActor (actor-based).
    - Collect quantitative metrics (attempted/succeeded/failed ops, drift, latency,
      throughput) to prove correctness under stress.
    - Core invariant: Drift == 0.00 in transfer-only (closed) scenarios.

    Thus, the simulator is both a load generator and a measurement tool for
    race conditions and system scalability.
    """

    def __init__(self,
                 accounts: List[object],
                 users: int,
                 ops_per_user: int,
                 transfer_prob: float = 0.5,
                 seed: int | None = None):
        assert users > 0 and ops_per_user > 0
        self.accounts = accounts
        self.users = users
        self.ops_per_user = ops_per_user
        self.transfer_prob = max(0.0, min(1.0, float(transfer_prob)))
        self._rng = random.Random(seed)

        # Shared metrics
        self._mtx = Lock()
        self._attempted = 0
        self._succeeded = 0
        self._failed = 0
        self._failed_by_reason = {
            'insufficient_funds': 0,
            'invalid_amount': 0,
            'same_account': 0,
            'other': 0,
        }
        self._latencies: List[float] = []  # seconds per op

    # ---------- helpers ----------
    def _pick_two(self) -> Tuple[object, object]:
        """Pick two accounts (can be the same if only one account exists)."""
        a, b = self._rng.sample(self.accounts, 2) if len(self.accounts) >= 2 else (self.accounts[0], self.accounts[0])
        return a, b

    def _amount(self) -> Decimal:
        """Generate a random amount between 0.01 and 50.00 (2dp)."""
        cents = self._rng.randint(1, 5000)
        return Decimal(cents).scaleb(-2).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    def _do_transfer(self):
        """
        Simulate a transfer between two accounts.
        - Handles insufficient funds, invalid amounts, or same-account cases.
        - Records latency and failure reasons.
        """
        src, dst = self._pick_two()
        if src is dst:
            with self._mtx:
                self._attempted += 1
                self._failed += 1
                self._failed_by_reason['same_account'] += 1
            return
        amt = self._amount()
        t0 = time.perf_counter()
        try:
            src.transfer_to(dst, amt)
            ok = True
        except InsufficientFunds:
            ok = False; reason = 'insufficient_funds'
        except InvalidAmount:
            ok = False; reason = 'invalid_amount'
        except Exception:
            ok = False; reason = 'other'
        t1 = time.perf_counter()
        with self._mtx:
            self._attempted += 1
            self._latencies.append(t1 - t0)
            if ok:
                self._succeeded += 1
            else:
                self._failed += 1
                self._failed_by_reason[reason] += 1

    def _do_dw(self):
        """
        Simulate a deposit or withdrawal.
        - Randomly chooses operation type.
        - Records success/failure and latency.
        """
        acc = self._rng.choice(self.accounts)
        amt = self._amount()
        op = 'deposit' if self._rng.random() < 0.5 else 'withdraw'
        t0 = time.perf_counter()
        try:
            if op == 'deposit':
                acc.deposit(amt)
            else:
                acc.withdraw(amt)
            ok = True
        except InsufficientFunds:
            ok = False; reason = 'insufficient_funds'
        except InvalidAmount:
            ok = False; reason = 'invalid_amount'
        except Exception:
            ok = False; reason = 'other'
        t1 = time.perf_counter()
        with self._mtx:
            self._attempted += 1
            self._latencies.append(t1 - t0)
            if ok:
                self._succeeded += 1
            else:
                self._failed += 1
                self._failed_by_reason[reason] += 1

    def _worker(self):
        """Worker thread: perform ops_per_user operations with mix of transfer/dw."""
        for _ in range(self.ops_per_user):
            if self._rng.random() < self.transfer_prob and len(self.accounts) >= 2:
                self._do_transfer()
            else:
                self._do_dw()

    # ---------- public ----------
    def run(self) -> Dict:
        """
        Run all worker threads, collect metrics, and return results dict.

        Returns a dict with:
        - attempted / succeeded / failed counts
        - failed.by_reason breakdown
        - throughput (ops/sec)
        - latency metrics (avg, p95)
        - total_drift (invariant in transfer-only scenarios)
        """
        def _total() -> Decimal:
            """Helper: compute total balance across all accounts."""
            tot = Decimal("0.00")
            for a in self.accounts:
                try:
                    bal = a.get_balance()
                except Exception:
                    # For actor models balance call may need tiny delay
                    time.sleep(0.001)
                    bal = a.get_balance()
                tot += Decimal(str(bal))
            return tot.quantize(Decimal("0.00"))

        start_total = _total()
        t0 = time.perf_counter()

        # Launch threads
        threads = [Thread(target=self._worker, daemon=True) for _ in range(self.users)]
        for th in threads: th.start()
        for th in threads: th.join()

        elapsed = max(time.perf_counter() - t0, 1e-9)
        end_total = _total()
        drift = (end_total - start_total).quantize(Decimal("0.00"))

        # latency metrics
        lats = sorted(self._latencies)
        avg_ms = (sum(lats) / len(lats) * 1000.0) if lats else 0.0
        p95_ms = (lats[int(0.95 * (len(lats) - 1))] * 1000.0) if lats else 0.0

        stats = {
            'attempted': {'total': self._attempted},
            'succeeded': {'total': self._succeeded},
            'failed': {
                'total': self._failed,
                'by_reason': self._failed_by_reason.copy(),
            },
            'ops_per_sec': float(self._attempted) / elapsed,
            'avg_latency_ms': round(avg_ms, 3),
            'p95_latency_ms': round(p95_ms, 3),
            'total_drift': drift,
        }
        return stats
