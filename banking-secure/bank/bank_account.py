# -*- coding: utf-8 -*-
from __future__ import annotations
"""
TR — Güvenlik ve Eşzamanlılık (NIST/OWASP) + Kritik Bölge Tanımı:
- Kritik Bölge (Critical Section): Programın, paylaşılan değişken/kaynak üzerinde atomik olması gereken
  kısmıdır; aynı anda yalnız bir iş parçası/proses tarafından yürütülmelidir (mutual exclusion).
  (ISO/IEC/IEEE 24765 — Systems & Software Engineering Vocabulary; genel tanım için bkz. OS literatürü)
- NIST SP 800-160 bağlamı: Paylaşılan kaynaklara deterministik erişim; yarış koşullarını tasarımla azalt.
- OWASP (Race Conditions/ASVS): Kritik bölgeleri kilitle, atomiklik ve bütünlüğü sağla; deadlock’u önlemek
  için kanonik kilit sırası uygula.

EN — Security & Concurrency (NIST/OWASP) + Critical Section:
- Critical Section: The portion of code that accesses shared mutable state and must not be executed by more
  than one thread/process at the same time (mutual exclusion). (ISO/IEC/IEEE 24765 vocabulary; see OS texts)
- NIST SP 800-160: Deterministic control over shared resources; design out race conditions.
- OWASP (Race Conditions/ASVS): Lock critical sections; preserve atomicity/integrity; use canonical lock
  ordering to avoid deadlocks.

Bu sınıf, hesap başına RLock ve transferlerde KANONİK KİLİT SIRASI (account_number) uygular.
GIL sebebiyle saf CPU-yoğun Python bytecode’unda gerçek çok çekirdekli paralellik beklemeyin; burada
gösterilen şey eşzamanlılık (işlerin örtüşmesi) ve bütünlük garantileridir.
"""

from decimal import Decimal
from threading import RLock
import time
import bank.config as cfg  # dinamik gecikmeyi runtime'da okuyabilmek için

class InsufficientFunds(Exception):
    pass

class BankAccount:
    def __init__(self, account_number: str, balance: Decimal):
        self.account_number = account_number
        self._balance = Decimal(balance)
        self._lock = RLock()

    # TR: Kritik bölge — atomiklik & bütünlük (OWASP). RLock ile yarış koşulları önlenir (NIST).
    # EN: Critical section — atomicity & integrity (OWASP). RLock prevents races (NIST).
    def deposit(self, amount: Decimal) -> None:
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        with self._lock:
            if cfg.CRIT_DELAY_SEC:
                time.sleep(cfg.CRIT_DELAY_SEC)
            self._balance += amount

    # TR: Kritik bölge — negatif bakiye kontrolü + atomik güncelleme.
    # EN: Critical section — insufficient-funds check + atomic update.
    def withdraw(self, amount: Decimal) -> None:
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        with self._lock:
            if self._balance < amount:
                raise InsufficientFunds("insufficient funds")
            if cfg.CRIT_DELAY_SEC:
                time.sleep(cfg.CRIT_DELAY_SEC)
            self._balance -= amount

    def get_balance(self) -> Decimal:
        with self._lock:
            return Decimal(self._balance)

    # TR: DEADLOCK ÖNLEME — KANONİK SIRA (OWASP/NIST)
    # EN: DEADLOCK AVOIDANCE — CANONICAL ORDER (OWASP/NIST)
    def transfer_to(self, other: "BankAccount", amount: Decimal) -> None:
        if self is other:
            raise ValueError("cannot transfer to the same account")
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")

        first, second = (self, other) if self.account_number < other.account_number else (other, self)
        with first._lock:
            with second._lock:
                if self._balance < amount:
                    raise InsufficientFunds("insufficient funds")
                # Kritik bölgeyi büyütmek için isteğe bağlı gecikme
                # Optional delay to enlarge the critical region
                if cfg.CRIT_DELAY_SEC:
                    time.sleep(cfg.CRIT_DELAY_SEC)
                self._balance -= amount
                other._balance += amount
