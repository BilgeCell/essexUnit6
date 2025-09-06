# -*- coding: utf-8 -*-
"""
Interactive Concurrent Banking Simulator

Purpose:
- Demonstrates concurrency control in a banking system.
- Provides three scenarios:
  1) Race Condition Test: Single Account Stress
  2) Hot-Spot: Intensive Transfers Between Two Accounts
  3) Scalability Test: System Throughput Across Many Accounts

Outputs:
- Prints human-readable tables with key metrics (success, throughput, drift).
- Writes all results to ./reports/sim_results.csv for reproducibility.
- Supports safe exits (Ctrl+C) and actor cleanup.
"""


from __future__ import annotations

from decimal import Decimal
from typing import Dict, List
import csv
import os
import time
from datetime import datetime

from bank.bank_account import BankAccount
from bank.bank_account_actor import BankAccountActor, warn_many_actors
from bank.transaction_simulator import TransactionSimulator
import bank.config as cfg

# ---------- Formatting & I/O ----------
REPORTS_DIR = os.path.join(os.getcwd(), "reports")
REPORT_CSV = os.path.join(REPORTS_DIR, "sim_results.csv")

def fmt_money(x: Decimal) -> str:
    symbol = cfg.CURRENCY_SYMBOLS.get(cfg.CURRENCY, '$')
    return f"{symbol}{Decimal(str(x)):,.2f}"

def pause() -> None:
    """Pause for user input (safe in case of non-interactive piping)."""
    try:
        input("\nPress Enter to continue... ")
    except (EOFError, KeyboardInterrupt):
        print("")

def ensure_reports_dir() -> None:
    if not os.path.isdir(REPORTS_DIR):
        os.makedirs(REPORTS_DIR, exist_ok=True)

def write_csv_row(row: Dict[str, object]) -> None:
    ensure_reports_dir()
    is_new = not os.path.exists(REPORT_CSV)
    fieldnames = [
        "timestamp","scenario","method","num_accounts","users","ops_per_user",
        "attempted","succeeded","failed","failed_insufficient","failed_invalid",
        "failed_same_account","failed_other",
        "ops_per_sec","avg_latency_ms","p95_latency_ms",
        "total_drift","currency","crit_delay_ms","transfer_only"
    ]
    with open(REPORT_CSV, mode="a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            w.writeheader()
        w.writerow(row)

def explain_drift_line(transfer_only: bool) -> str:
    if transfer_only:
        return ("(Final Total - Initial Total. Must be £0.00 in transfer-only (conservative) scenarios. "
                "Non-zero drift would indicate a critical correctness bug.)")
    return ("(Final Total - Initial Total. In deposit/withdraw contention (non-conservative) scenarios, "
            "positive drift is expected because failed withdrawals do not remove funds while deposits succeed.)")

def print_results_table(stats: Dict, *, transfer_only: bool) -> None:
    succeeded = stats.get('succeeded', {}).get('total', 0)
    attempted = stats.get('attempted', {}).get('total', 0)
    ops_per_sec = stats.get('ops_per_sec', 0.0)
    drift = stats.get('total_drift', Decimal("0"))

    print("\n  --- Simulation Results ---")
    print("  " + "=" * 45)
    print(f"  {'Succeeded / Attempted Ops':<28}: {succeeded:,}/{attempted:,}")
    print(f"  {'':<30}  (Successful ops vs. total attempted. Failures can occur, e.g., due to insufficient funds.)")
    print(f"  {'Throughput (Ops/Sec)':<28}: {float(ops_per_sec):,.0f}")
    print(f"  {'':<30}  (Measures system performance under load. Higher is better.)")
    print(f"  {'Total Money Drift':<28}: {fmt_money(Decimal(str(drift)))}")
    print(f"  {'':<30}  {explain_drift_line(transfer_only)}")
    print("  " + "=" * 45)

def run_method(method_name: str,
               accounts: List[object],
               users: int,
               ops_per_user: int,
               transfer_only: bool,
               scenario_title: str,
               stats: Dict) -> None:
    print(f"\n[{method_name}]")
    print("-> Simulation in progress... Please wait.")
    print_results_table(stats, transfer_only=transfer_only)

    write_csv_row({
        'timestamp': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'scenario': scenario_title,
        'method': method_name,
        'num_accounts': len(accounts),
        'users': users,
        'ops_per_user': ops_per_user,
        'attempted': stats.get('attempted', {}).get('total', 0),
        'succeeded': stats.get('succeeded', {}).get('total', 0),
        'failed': int(stats.get('failed', {}).get('total', 0)),
        'failed_insufficient': int(stats.get('failed', {}).get('by_reason', {}).get('insufficient_funds', 0)),
        'failed_invalid': int(stats.get('failed', {}).get('by_reason', {}).get('invalid_amount', 0)),
        'failed_same_account': int(stats.get('failed', {}).get('by_reason', {}).get('same_account', 0)),
        'failed_other': int(stats.get('failed', {}).get('by_reason', {}).get('other', 0)),
        'ops_per_sec': float(stats.get('ops_per_sec', 0.0)),
        'avg_latency_ms': float(stats.get('avg_latency_ms', 0.0)),
        'p95_latency_ms': float(stats.get('p95_latency_ms', 0.0)),
        'total_drift': str(stats.get('total_drift', "0.00")),
        'currency': cfg.CURRENCY,
        'crit_delay_ms': round(float(cfg.CRIT_DELAY_SEC) * 1000.0, 3),
        'transfer_only': transfer_only,
    })

def safe_stop_actors(accounts: List[object]) -> None:
    for acc in accounts:
        if hasattr(acc, 'stop') and callable(getattr(acc, 'stop')):
            try:
                acc.stop()
            except Exception:
                pass

def run_predefined_scenario(title: str, explanation: str, num_accounts: int, users: int, ops: int,
                            *, transfer_only: bool) -> None:
    print(f"\n--- {title} ---")
    print(explanation.format(users=users, ops=f"{ops:,}", num_accounts=num_accounts))

    # Method A — Lock/RLock
    accounts_a = [BankAccount(f"A{i:02d}", Decimal("1000")) for i in range(num_accounts)]
    sim_a = TransactionSimulator(accounts_a, users, ops_per_user=ops, transfer_prob=1.0 if transfer_only else 0.0)
    stats_a = sim_a.run()
    run_method("Method A — Lock/RLock (Pessimistic Locking)", accounts_a, users, ops, transfer_only, title, stats_a)

    # Method B — Actor/Queue
    warn_many_actors(num_accounts)
    accounts_b = [BankAccountActor(f"B{i:02d}", Decimal("1000")) for i in range(num_accounts)]
    sim_b = TransactionSimulator(accounts_b, users, ops_per_user=ops, transfer_prob=1.0 if transfer_only else 0.0)
    try:
        stats_b = sim_b.run()
        run_method("Method B — Actor/Queue (Message-Passing)", accounts_b, users, ops, transfer_only, title, stats_b)
    finally:
        safe_stop_actors(accounts_b)

    print(f"\nCSV updated → {REPORT_CSV}")
    pause()

def menu_assignment_scenarios() -> None:
    # Clear, first-glance-friendly English labels
    scenario1_title = "Race Condition Test: Single Account Stress"
    scenario2_title = "Hot-Spot: Intensive Transfers Between Two Accounts"
    scenario3_title = "Scalability Test: System Throughput Across Many Accounts"

    scenario1_desc = (
        "This scenario stresses a single shared account to surface race conditions.\n"
        "*{users} users will perform {ops} random deposit/withdraw operations on ONE account.*\n"
        "Note: This is a non-conservative flow; due to failed withdrawals, positive drift is expected and does not indicate a race bug."
    )
    scenario2_desc = (
        "This scenario concentrates traffic between TWO accounts (a hot-spot) and checks money conservation.\n"
        "*{users} users will perform transfers ONLY between two accounts.* Expected drift is £0.00 (closed system)."
    )
    scenario3_desc = (
        "This scenario distributes transfers across many accounts to measure scalability/throughput under load.\n"
        "*{users} users will perform transfers across {num_accounts} accounts.*"
    )

    while True:
        try:
            print("\n=== Assignment Scenarios ===")
            print(f"1) {scenario1_title}")
            print(f"2) {scenario2_title}")
            print(f"3) {scenario3_title}")
            print("0) Back to Main Menu")
            choice = input("Choice: ").strip()

            if choice == "1":
                run_predefined_scenario(
                    scenario1_title, scenario1_desc,
                    num_accounts=1, users=16, ops=20000, transfer_only=False
                )
            elif choice == "2":
                run_predefined_scenario(
                    scenario2_title, scenario2_desc,
                    num_accounts=2, users=16, ops=20000, transfer_only=True
                )
            elif choice == "3":
                run_predefined_scenario(
                    scenario3_title, scenario3_desc,
                    num_accounts=50, users=64, ops=5000, transfer_only=True
                )
            elif choice == "0":
                break
            else:
                print("Invalid choice.")
        except KeyboardInterrupt:
            print("\nReturning to main menu...")
            break

def delay_settings_menu() -> None:
    print(f"\nCurrent artificial delay: {cfg.CRIT_DELAY_SEC*1000:.2f} ms")
    s = input("Enter new value in ms (0=off, blank=cancel): ").strip()
    if not s:
        return
    try:
        ms = float(s)
        if ms < 0:
            raise ValueError
        cfg.CRIT_DELAY_SEC = ms / 1000.0
        print(f"New delay set to: {cfg.CRIT_DELAY_SEC*1000:.2f} ms")
    except (ValueError, TypeError):
        print("Invalid value.")

def main() -> None:
    symbol = cfg.CURRENCY_SYMBOLS.get(cfg.CURRENCY, '$')
    print("== Thread-Safe Banking CLI ==")
    print(f"Currency: {cfg.CURRENCY} ({symbol})")
    print(f"Default starting balance per account: {fmt_money(Decimal('1000'))}")
    print(f"Current artificial delay: {cfg.CRIT_DELAY_SEC * 1000:.1f} ms\n")

    while True:
        try:
            print("\n=== Main Menu ===")
            print("1) Run Assignment Scenarios")
            print("2) Delay Settings")
            print("0) Quit")
            sel = input("Choice: ").strip()

            if sel == "0":
                print("Goodbye.")
                break
            elif sel == "1":
                menu_assignment_scenarios()
            elif sel == "2":
                delay_settings_menu()
                pause()
            else:
                print("Invalid choice.")
                pause()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

if __name__ == "__main__":
    main()
