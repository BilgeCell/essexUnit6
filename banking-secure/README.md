# Secure and Concurrent Banking System Simulation

## 1. Project Goal & Assignment Context

This project implements a thread-safe banking system as required by the "Object-Oriented Software Development" assignment. The primary goal is to demonstrate the successful application of concurrency control mechanisms to prevent critical issues like **race conditions** and **deadlocks**.

To showcase a comprehensive understanding, this project implements and compares two distinct industry-standard approaches:

1.  **Method A: Pessimistic Locking (`RLock`)**: A traditional approach using locks to protect shared resources. This method demonstrates disciplined concurrency control, including a strict **canonical lock-ordering policy** to prevent deadlocks, a direct application of OWASP guidelines.
2.  **Method B: Actor Model (Message Passing)**: A modern, lock-free approach that avoids shared state. By design, this architecture eliminates the possibility of race conditions, aligning with the principles of secure system design championed by standards like NIST.

This dual implementation provides a practical comparison of concurrency trade-offs, directly addressing the core learning outcomes of the assignment.

## 2. Core Concepts & Security Principles

* **Critical Section**: Per ISO/IEC/IEEE 24765, a critical section is "a part of a program that accesses shared resources and must not be concurrently executed by more than one thread." In this project, all balance mutations are performed within these protected sections.
* **Race Condition Prevention (OWASP ASVS)**: In Method A, critical sections are protected by `threading.RLock`. In Method B, since there is no shared mutable state, race conditions are structurally impossible. This demonstrates two different strategies to achieve the same security goal.
* **Deadlock Prevention (OWASP ASVS)**: Method A's transfer operation implements a canonical lock ordering strategy (ordering by `account_number`) to provably prevent deadlocks.
* **Data Integrity & Input Validation (OWASP ASVS)**: The system uses Python's `Decimal` with banker's rounding for all financial calculations to prevent floating-point errors. All transaction amounts are validated against business limits defined in `config.py`.
* **System Resilience (NIST SP 800-160)**: The choice of these architectures provides deterministic control over resources, which reduces complexity and increases system resilience, a core tenant of NIST's guidelines for secure software engineering.
* **Atomicity & Consistency**:
    * **Method A (Locking)** achieves strict atomicity for transfers by holding both account locks simultaneously.
    * **Method B (Actor)** implements transfers with a compensation-based approach (saga-like). It guarantees **eventual consistency** without deadlocks, presenting a different consistency model trade-off.

## 3. Architectural Overview: The Role of Each Class

* **`BankAccount` Class** (`bank/bank_account.py`): The lock-based implementation (Method A). Its core duty is to protect the shared balance data using traditional `RLock` mechanisms and prevent deadlocks with canonical lock ordering.
* **`BankAccountActor` Class** (`bank/bank_account_actor.py`): The lock-free, actor-model implementation (Method B). It processes operations sequentially via a private message queue to guarantee data integrity without locks.
* **`TransactionSimulator` Class** (`bank/transaction_simulator.py`): The simulation engine required by the assignment. It stress-tests the bank account models with thousands of concurrent transactions to empirically prove their thread-safety.
* **`TestBankingSystem` Class** (`tests/test_banking_system.py`): The project's quality assurance suite. It contains automated tests to verify functionality and system integrity under high concurrency.
* **`InsufficientFunds` & `InvalidAmount` Classes** (`bank/errors.py`): Custom exception classes that provide specific, meaningful errors for robust error handling.

## 4. How to Run the Application

1.  **Install Dependencies** (pytest for testing):
    ```bash
    pip install pytest
    ```
2.  **Run Unit & Concurrency Tests** (Recommended):
    ```bash
    pytest -v
    ```
    *(Alternative: `python -m unittest discover -v`)*
3.  **Run the Interactive CLI**:
    ```bash
    python main.py
    ```

## 5. Meeting Assignment Criteria

* **[✓] `BankAccount` Class**: Implemented in `bank/bank_account.py`.
* **[✓] Thread Safety**: Achieved via `RLock` (Method A) and the Actor Model (Method B).
* **[✓] `TransactionSimulator` Class**: Implemented and used by the CLI to run all demonstrations.
* **[✓] Deadlock Prevention**: Handled and documented in `bank/bank_account.py`.
* **[✓] Testing and Validation**: A comprehensive test suite is provided in `tests/test_banking_system.py`, validating correctness and data integrity under load.
* **[✓] Documentation & Structure**: The project is modular, well-commented, and uses a central configuration.

## 6. Production Readiness & Further Improvements

* **Actor Thread Lifecycle**: For this assignment, actors run on `daemon=True` threads. Production systems would require graceful shutdown to drain message queues.
* **Code Quality**: The code adheres to clean code principles. Integrating static analysis tools (`ruff`, `mypy`) in a CI/CD pipeline would be the next step for a production environment.