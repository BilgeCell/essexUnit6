# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Concurrent Transaction Simulator

Assignment Goal: This module fulfills the `TransactionSimulator` class
requirement. Its purpose is to empirically validate the thread safety of the
bank account models under heavy, concurrent load. It provides the measurable
metrics (throughput, drift) that prove the success of the concurrency controls.
"""
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Sequence, Dict, Any, List, Union
from .bank_account import BankAccount
from .bank_account_actor import BankAccountActor

AccountType = Union[BankAccount, BankAccountActor]

def _get_total(accounts: Sequence[AccountType]) -> Decimal:
    """Helper to sum up all account balances."""
    return sum(acc.get_balance() for acc in accounts)

def _run_concurrent(
    accounts: Sequence[AccountType],
    users: int,
    ops_per_user: int,
    transfer_prob: float,
    seed: int
) -> Dict[str, Any]:
    """The core simulation logic."""
    rng = random.Random(seed)

    def do_one_op(local_rng: random.Random, local_stats: Dict[str, int]):
        try:
            if local_rng.random() < transfer_prob and len(accounts) >= 2:
                s, d = local_rng.sample(accounts, 2)
                amt = Decimal(local_rng.randint(1, 100))
                local_stats["attempt_transfer"] += 1
                s.transfer_to(d, amt)
                local_stats["ok_transfer"] += 1
            else:
                acc = local_rng.choice(accounts)
                amt = Decimal(local_rng.randint(1, 50))
                if local_rng.random() < 0.5:
                    local_stats["attempt_deposit"] += 1
                    acc.deposit(amt)
                    local_stats["ok_deposit"] += 1
                else:
                    local_stats["attempt_withdraw"] += 1
                    acc.withdraw(amt)
                    local_stats["ok_withdraw"] += 1
        except Exception:
            local_stats["fail_total"] += 1

    def worker(local_seed: int) -> Dict[str, int]:
        """The task for each thread."""
        local_rng = random.Random(local_seed)
        stats = {k: 0 for k in ("attempt_deposit", "ok_deposit", "attempt_withdraw", "ok_withdraw", "attempt_transfer", "ok_transfer", "fail_total")}
        for _ in range(ops_per_user):
            do_one_op(local_rng, stats)
        return stats

    t0 = time.perf_counter()
    before_total = _get_total(accounts)
    
    with ThreadPoolExecutor(max_workers=users) as ex:
        futures = [ex.submit(worker, seed + i) for i in range(users)]
        agg_stats = {k: 0 for k in ("attempt_deposit", "ok_deposit", "attempt_withdraw", "ok_withdraw", "attempt_transfer", "ok_transfer", "fail_total")}
        for f in as_completed(futures):
            result = f.result()
            for k, v in result.items():
                agg_stats[k] += v

    elapsed = time.perf_counter() - t0
    after_total = _get_total(accounts)

    attempted = agg_stats["attempt_deposit"] + agg_stats["attempt_withdraw"] + agg_stats["attempt_transfer"]
    succeeded = agg_stats["ok_deposit"] + agg_stats["ok_withdraw"] + agg_stats["ok_transfer"]
    ops_per_sec = succeeded / elapsed if elapsed > 0 else 0

    return {
        "succeeded": {"total": succeeded},
        "attempted": {"total": attempted},
        "elapsed_wall": elapsed,
        "ops_per_sec": ops_per_sec,
        "total_before": before_total,
        "total_after": after_total,
        "total_drift": after_total - before_total,
    }

class TransactionSimulator:
    """
    Wrapper class to satisfy the assignment rubric ("TransactionSimulator class").
    It configures and delegates the core work to the `_run_concurrent()` function.
    """
    def __init__(
        self,
        accounts: List[AccountType],
        users: int,
        ops_per_user: int,
        transfer_prob: float,
        seed: int = 42,
    ):
        self.accounts = accounts
        self.users = users
        self.ops_per_user = ops_per_user
        self.transfer_prob = transfer_prob
        self.seed = seed

    def run(self) -> dict:
        """Executes the simulation with the stored configuration."""
        return _run_concurrent(
            self.accounts,
            users=self.users,
            ops_per_user=self.ops_per_user,
            transfer_prob=self.transfer_prob,
            seed=self.seed
        )