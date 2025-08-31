# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for the Banking System.

Assignment Goal: This test suite fulfills the "Testing and Validation"
requirement. It provides automated quality assurance for the entire system.

- Philosophy: "Trust, but verify." This code proves the correctness of the
  concurrency models under stress.
- Key Test: The `test_high_concurrency_integrity_*` methods are the most
  critical. They simulate a closed economy (transfers only) and assert that
  the total money "drift" is zero. This is the definitive, automated proof
  that our concurrency controls prevent data corruption.
"""
import unittest
import time
from decimal import Decimal

from bank.bank_account import BankAccount
from bank.bank_account_actor import BankAccountActor
from bank.transaction_simulator import TransactionSimulator
from bank.errors import InsufficientFunds, InvalidAmount

class TestBankingSystem(unittest.TestCase):
    def test_deposit_and_withdraw(self):
        """Tests basic, single-threaded account operations."""
        acc = BankAccount("T001", Decimal("100.00"))
        acc.deposit(Decimal("50.50"))
        self.assertEqual(acc.get_balance(), Decimal("150.50"))
        acc.withdraw(Decimal("20.00"))
        self.assertEqual(acc.get_balance(), Decimal("130.00"))

    def test_error_conditions(self):
        """Tests that the system correctly raises errors for invalid operations."""
        acc = BankAccount("T002", Decimal("100.00"))
        with self.assertRaises(InvalidAmount):
            acc.deposit(Decimal("-10.00"))
        with self.assertRaises(InsufficientFunds):
            acc.withdraw(Decimal("100.01"))

    def test_lock_based_transfer(self):
        """Tests a simple, single-threaded transfer for the Lock-based model."""
        a1 = BankAccount("T_LOCK_1", Decimal("200.00"))
        a2 = BankAccount("T_LOCK_2", Decimal("50.00"))
        a1.transfer_to(a2, Decimal("75.00"))
        self.assertEqual(a1.get_balance(), Decimal("125.00"))
        self.assertEqual(a2.get_balance(), Decimal("125.00"))

    def test_actor_based_transfer(self):
        """Tests a simple, single-threaded transfer for the Actor-based model."""
        b1 = BankAccountActor("T_ACTOR_1", Decimal("200.00"))
        b2 = BankAccountActor("T_ACTOR_2", Decimal("50.00"))
        b1.transfer_to(b2, Decimal("75.00"))
        time.sleep(0.05) # Allow time for async operation to complete
        self.assertEqual(b1.get_balance(), Decimal("125.00"))
        self.assertEqual(b2.get_balance(), Decimal("75.00"))
        b1.stop(); b2.stop()

    def _run_integrity_test(self, account_class, num_accounts=10):
        """Helper to run the same high-concurrency test on different account types."""
        accounts = [account_class(f"C_{i}", Decimal("1000")) for i in range(num_accounts)]
        
        sim = TransactionSimulator(
            accounts=accounts,
            users=16,
            ops_per_user=1000,
            transfer_prob=1.0  # Transfer-only to test for zero drift
        )
        stats = sim.run()

        self.assertEqual(stats['total_drift'], Decimal("0.00"),
                         f"{account_class.__name__} failed integrity test: money was lost or created.")
        
        if account_class == BankAccountActor:
            for acc in accounts:
                if hasattr(acc, 'stop'):
                    acc.stop()

    def test_high_concurrency_integrity_lock_based(self):
        """Validates the thread safety of the RLock-based implementation."""
        self._run_integrity_test(BankAccount)

    def test_high_concurrency_integrity_actor_based(self):
        """Validates the thread safety of the Actor Model implementation."""
        self._run_integrity_test(BankAccountActor)

if __name__ == '__main__':
    unittest.main(verbosity=2)