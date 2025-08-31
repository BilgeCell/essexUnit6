# -*- coding: utf-8 -*-
"""
Interactive Concurrent Banking Simulator CLI

Philosophy: This interface is a focused laboratory environment for demonstrating
and testing concurrency concepts. The main menu is streamlined to center on the
core "Assignment Scenarios", providing clear, explained results for easy evaluation.
The goal is to guide the user (the instructor) through a curated demonstration
that directly proves the assignment requirements have been met.
"""
from decimal import Decimal
import time
from typing import Dict, List

from bank.bank_account import BankAccount
from bank.bank_account_actor import BankAccountActor
from bank.transaction_simulator import TransactionSimulator
import bank.config as cfg

# ============== Display / Formatting ==============
def fmt_money(x: Decimal) -> str:
    """Formats a Decimal value as a currency string."""
    symbol = cfg.CURRENCY_SYMBOLS.get(cfg.CURRENCY, '$')
    return f"{symbol}{x:,.2f}"

def pause():
    """Pauses the execution until the user presses Enter."""
    input("\nPress Enter to continue... ")

# ============== Menus ==============
def print_results_table(stats: Dict):
    """Prints simulation results in a clear, explained, table-like format."""
    succeeded = stats['succeeded']['total']
    attempted = stats['attempted']['total']
    ops_per_sec = stats.get('ops_per_sec', 0)
    drift = stats['total_drift']

    succeeded_str = f"{succeeded:,}/{attempted:,}"
    ops_per_sec_str = f"{ops_per_sec:,.0f}"
    drift_str = fmt_money(drift)

    print("\n  --- Simulation Results ---")
    print("  " + "="*45)
    print(f"  {'Succeeded / Attempted Ops':<28}: {succeeded_str}")
    print(f"  {'':<30}  (Successful ops vs. total attempted. Failures can occur, e.g., due to insufficient funds.)")
    print(f"  {'Throughput (Ops/Sec)':<28}: {ops_per_sec_str}")
    print(f"  {'':<30}  (Measures system performance under load. Higher is better.)")
    print(f"  {'Total Money Drift':<28}: {drift_str}")
    print(f"  {'':<30}  (Final Total - Initial Total. **Must be £0.00 in transfer-only scenarios.** Non-zero drift indicates a critical bug.)")
    print("  " + "="*45)

def run_predefined_scenario(title: str, explanation: str, num_accounts: int, users: int, ops: int):
    """Runs a predefined simulation scenario with clear explanations."""
    print(f"\n--- {title} ---")
    print(explanation.format(users=users, ops=f"{ops:,}", num_accounts=num_accounts))

    # --- Run for Method A (Lock-based) ---
    accounts_a = [BankAccount(f"A{i:02d}", Decimal("1000")) for i in range(num_accounts)]
    transfer_prob = 1.0 if "transfer" in explanation.lower() else 0.0
    print(f"\n[Method A — Lock/RLock (Pessimistic Locking)]")
    print("-> Simulation in progress... Please wait.")
    sim_a = TransactionSimulator(accounts_a, users, ops_per_user=ops, transfer_prob=transfer_prob)
    stats_a = sim_a.run()
    print_results_table(stats_a)

    # --- Run for Method B (Actor-based) ---
    accounts_b = [BankAccountActor(f"B{i:02d}", Decimal("1000")) for i in range(num_accounts)]
    print(f"\n[Method B — Actor/Queue (Message-Passing)]")
    print("-> Simulation in progress... Please wait.")
    sim_b = TransactionSimulator(accounts_b, users, ops_per_user=ops, transfer_prob=transfer_prob)
    stats_b = sim_b.run()
    print_results_table(stats_b)
    
    # Clean up actor threads after the scenario
    for acc in accounts_b:
        if hasattr(acc, 'stop'):
            acc.stop()
    pause()

def menu_assignment_scenarios():
    """The main menu for running the required assignment scenarios."""
    scenario1_desc = (
        "This scenario tests 'Single Account Contention' to detect **Race Conditions**.\n"
        "A **Race Condition** occurs when multiple users try to modify the same data (the balance) at the exact same time. Without protection, operations can overwrite each other, leading to data corruption.\n\n"
        "*Here, {users} users will stress-test a single account with {ops} random deposit/withdraw operations.*"
    )
    scenario2_desc = (
        "This scenario tests a 'Hot-Spot' and focuses on **Total Money Drift**.\n"
        "**Drift** is the final total money minus the initial total. In a closed system with transfers only, the drift **must be zero**. A non-zero drift proves a critical bug exists.\n\n"
        "*Here, {users} users will only perform transfers between two accounts. The expected drift is £0.00.*"
    )
    scenario3_desc = (
        "This scenario tests 'Scalability' by measuring **Throughput**.\n"
        "**Throughput** (ops/sec) is how many operations a system can handle. This test shows how each method performs when the workload is distributed across many accounts, simulating a real-world system.\n\n"
        "*Here, {users} users will perform transfers across {num_accounts} accounts to see which architecture is more efficient at scale.*"
    )
    
    while True:
        print("\n=== Assignment Scenarios ===")
        print("1) Single Account Contention (Detect Race Conditions)")
        print("2) Hot-Spot Contention (Check for Money Drift)")
        print("3) Scalability Test (Measure Throughput)")
        print("0) Back to Main Menu")
        choice = input("Choice: ").strip()

        if choice == "1":
            run_predefined_scenario("Scenario 1: Single Account Contention", scenario1_desc, 1, 16, 20000)
        elif choice == "2":
            run_predefined_scenario("Scenario 2: Hot-Spot", scenario2_desc, 2, 16, 20000)
        elif choice == "3":
            run_predefined_scenario("Scenario 3: Scalability", scenario3_desc, 50, 64, 5000)
        elif choice == "0":
            break
        else:
            print("Invalid choice.")

def delay_settings_menu():
    """Menu to adjust the artificial delay in critical sections."""
    print(f"\nCurrent artificial delay: {cfg.CRIT_DELAY_SEC*1000:.2f} ms")
    s = input("Enter new value in ms (0=off, blank=cancel): ").strip()
    if not s:
        return
    try:
        ms = float(s)
        if ms < 0: raise ValueError
        cfg.CRIT_DELAY_SEC = ms/1000.0
        print(f"New delay set to: {cfg.CRIT_DELAY_SEC*1000:.2f} ms")
    except (ValueError, TypeError):
        print("Invalid value.")

def main():
    """Main entry point for the CLI application."""
    symbol = cfg.CURRENCY_SYMBOLS.get(cfg.CURRENCY, '$')
    print("== Thread-Safe Banking CLI ==")
    print(f"Currency: {cfg.CURRENCY} ({symbol})")
    print(f"Default starting balance per account in scenarios: {fmt_money(Decimal('1000'))}")
    print(f"Current artificial delay: {cfg.CRIT_DELAY_SEC * 1000:.1f} ms\n")

    while True:
        print("\n=== Main Menu ===")
        print("1) Run Assignment Scenarios")
        print("2) Delay Settings")
        print("0) Quit")
        sel = input("Choice: ").strip()
        
        if sel == "0":
            print("Goodbye."); break
        elif sel == "1":
            menu_assignment_scenarios()
        elif sel == "2":
            delay_settings_menu(); pause()
        else:
            print("Invalid choice."); pause()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye.")
