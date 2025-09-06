# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for the Banking System.

Educational purpose:
- Demonstrates and validates concurrency control with two models:
  (A) Lock-based using RLock
  (B) Actor-based using message queues
- Key invariant in closed (transfer-only) economy: total drift must be 0.00
  → proves that money is neither lost nor created.
- Also shows that in non-conservative flows (deposit/withdraw with failures),
  positive drift can appear naturally and is not a bug.
"""

import unittest
import time
from decimal import Decimal, ROUND_HALF_EVEN

from bank.bank_account import BankAccount
from bank.bank_account_actor import BankAccountActor
from bank.transaction_simulator import TransactionSimulator
from bank.errors import InsufficientFunds, InvalidAmount


def _as_money(d) -> Decimal:
    """Normalize any numeric/string/Decimal to Decimal('0.00')."""
    return Decimal(str(d)).quantize(Decimal("0.00"), rounding=ROUND_HALF_EVEN)


class TestBankingSystem(unittest.TestCase):
    def test_deposit_and_withdraw(self):
        """Basic single-threaded operations."""
        acc = BankAccount("T001", Decimal("100.00"))
        acc.deposit(Decimal("50.50"))
        self.assertEqual(acc.get_balance(), Decimal("150.50"))
        acc.withdraw(Decimal("20.00"))
        self.assertEqual(acc.get_balance(), Decimal("130.00"))

    def test_error_conditions(self):
        """Invalid amount and insufficient funds should raise."""
        acc = BankAccount("T002", Decimal("100.00"))
        with self.assertRaises(InvalidAmount):
            acc.deposit(Decimal("-10.00"))
        with self.assertRaises(InsufficientFunds):
            acc.withdraw(Decimal("100.01"))

    def test_lock_based_transfer(self):
        """Single-threaded transfer for Lock-based model."""
        a1 = BankAccount("T_LOCK_1", Decimal("200.00"))
        a2 = BankAccount("T_LOCK_2", Decimal("50.00"))
        a1.transfer_to(a2, Decimal("75.00"))
        self.assertEqual(a1.get_balance(), Decimal("125.00"))
        self.assertEqual(a2.get_balance(), Decimal("125.00"))

    def test_actor_based_transfer(self):
        """Single-threaded transfer for Actor-based model."""
        b1 = BankAccountActor("T_ACTOR_1", Decimal("200.00"))
        b2 = BankAccountActor("T_ACTOR_2", Decimal("50.00"))
        try:
            b1.transfer_to(b2, Decimal("75.00"))
            time.sleep(0.05)  # allow async processing to complete
            self.assertEqual(b1.get_balance(), Decimal("125.00"))
            # FIX: expected 125.00 (50 + 75), not 75.00
            self.assertEqual(b2.get_balance(), Decimal("125.00"))
        finally:
            if hasattr(b1, "stop"): b1.stop()
            if hasattr(b2, "stop"): b2.stop()

    def _run_integrity_test(self, account_class, num_accounts=10, users=16, ops_per_user=1000):
        """
        High-concurrency integrity test on transfer-only workload.
        Invariant: total drift == 0.00; also assert attempted/succeeded sanity.
        """
        accounts = [account_class(f"C_{i:02d}", Decimal("1000.00")) for i in range(num_accounts)]
        try:
            sim = TransactionSimulator(
                accounts=accounts,
                users=users,
                ops_per_user=ops_per_user,
                transfer_prob=1.0  # transfer-only -> closed system
            )
            stats = sim.run()

            # Sanity checks on counters
            attempted_expected = users * ops_per_user
            attempted = int(stats.get("attempted", {}).get("total", 0))
            succeeded = int(stats.get("succeeded", {}).get("total", 0))
            self.assertEqual(
                attempted, attempted_expected,
                f"attempted ops mismatch: got {attempted}, expected {attempted_expected}"
            )
            self.assertLessEqual(
                succeeded, attempted,
                "succeeded ops must be <= attempted ops"
            )

            # Drift must be exactly 0.00 in transfer-only scenarios
            drift = _as_money(stats.get("total_drift", "0.00"))
            self.assertEqual(
                drift, Decimal("0.00"),
                f"{account_class.__name__} failed integrity test: non-zero drift = {drift}"
            )
        finally:
            if account_class == BankAccountActor:
                for acc in accounts:
                    if hasattr(acc, 'stop'):
                        acc.stop()

    def test_high_concurrency_integrity_lock_based(self):
        """Validates thread-safety of RLock-based implementation."""
        self._run_integrity_test(BankAccount)

    def test_high_concurrency_integrity_actor_based(self):
        """Validates actor-model implementation."""
        self._run_integrity_test(BankAccountActor)

    def test_non_conservative_contention_allows_positive_drift(self):
        """
        Educational check: In deposit/withdraw contention (non-conservative),
        a positive drift can legitimately occur due to failed withdrawals.
        This is NOT a correctness bug by itself.
        """
        accounts = [BankAccount("NC_00", Decimal("1000.00"))]
        sim = TransactionSimulator(
            accounts=accounts,
            users=8,
            ops_per_user=2000,
            transfer_prob=0.0  # NOT transfer-only
        )
        stats = sim.run()
        drift = _as_money(stats.get("total_drift", "0.00"))
        self.assertGreaterEqual(
            drift, Decimal("0.00"),
            f"Unexpected negative drift in non-conservative flow: {drift}"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
