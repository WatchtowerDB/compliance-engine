#!/usr/bin/env python3

import os
from pathlib import Path

from .models.download_model import download_model
from .scripts.pci_compliance_checker import PCIComplianceChecker

SCRIPT_DIR = Path(__file__).parent
MODEL_PATH: Path = Path(
    os.getenv(
        "WTCE_MODEL_PATH",
        SCRIPT_DIR.parent
        / "engine/models/base/Ministral-8B-Instruct-2410-GGUF/Ministral-8B-Instruct-2410-Q6_K_L.gguf",
    )
)
CHROMA_DIR: Path = Path(
    os.getenv("WTCE_CHROMA_DIR", SCRIPT_DIR.parent.parent.parent / "data/chroma_db")
)

if not MODEL_PATH.exists():
    # There already are guardrails within this function but container logic is a little hard to predict.
    download_model(
        "bartowski/Ministral-8B-Instruct-2410-GGUF",
        "Ministral-8B-Instruct-2410-GGUF",
        ["Ministral-8B-Instruct-2410-Q6_K_L.gguf"],
    )


# Example schema with multiple PCI-DSS violations
"""
    The violations:
    credit_card_number VARCHAR(16),  -- Violation: Unencrypted PAN
    cvv VARCHAR(4),                  -- Violation: Storing CVV (prohibited)

    card_number VARCHAR(16),         -- Violation: Unencrypted PAN

    pan VARCHAR(19),                 -- Violation: Unencrypted PAN
    security_code VARCHAR(4)         -- Violation: Storing CVV

    If the model works, it should generate at least 5 assertions. InshaAllah.
"""
SQL_SCHEMA = """
CREATE TABLE customers (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255),
    credit_card_number VARCHAR(16),  -- Violation: Unencrypted PAN
    cvv VARCHAR(4),                  -- Violation: Storing CVV (prohibited)
    expiration_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    transaction_id INT PRIMARY KEY,
    customer_id INT,
    amount DECIMAL(10, 2),
    transaction_date TIMESTAMP,
    card_number VARCHAR(16),         -- Violation: Unencrypted PAN
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE payment_methods (
    id INT PRIMARY KEY,
    user_id INT,
    card_holder_name VARCHAR(100),
    pan VARCHAR(19),                 -- Violation: Unencrypted PAN
    expiry VARCHAR(7),
    security_code VARCHAR(4)         -- Violation: Storing CVV
);
"""

# Initialize the PCI compliance checker
checker = PCIComplianceChecker(
    model_path=MODEL_PATH, chroma_dir=CHROMA_DIR, collection_name="PCI-DSS-v4.0.1"
)

print("=" * 80)
print("STEP 1: GENERATING SQL ASSERTIONS")
print("=" * 80)

# Generate SQL assertions
assertions = checker.generate_assertions(SQL_SCHEMA)

print("\n" + "=" * 80)
print("GENERATED ASSERTIONS (to be executed by external team):")
print("=" * 80)
for i, assertion in enumerate(assertions, 1):
    print(f"\n[Assertion {i}]")
    print(assertion)
    print("-" * 80)

print("\n" + "=" * 80)
print("STEP 2: SIMULATING FAILED ASSERTIONS")
print("=" * 80)

# In prod, these would come from external execution. These values are mock (or as close I can get to it :P)
failed_assertions = {
    "SELECT * FROM customers WHERE credit_card_number IS NOT NULL AND credit_card_number NOT LIKE '%[a-fA-F0-9]%'": "id: 1, credit_card_number: 5555 5555 5555 4444",
    "SELECT * FROM transactions WHERE card_number IS NOT NULL AND card_number NOT LIKE '%[a-fA-F0-9]%'": "transaction_id: 1, card_number: 5200 8282 8282 8210",
}
print(f"Failed_assertions (mock): {failed_assertions}\n")

print("\n" + "=" * 80)
print("STEP 3: ANALYZING FAILED ASSERTIONS")
print("=" * 80)

# Analyze each failed assertion
for i, (assertion, result) in enumerate(failed_assertions.items(), 1):
    print(f"\n{'=' * 80}")
    print(f"ANALYZING FAILURE {i}/{len(failed_assertions)}")
    print(f"{'=' * 80}")
    print("\nFailed Assertion:")
    print(f"{assertion}\n")
    print("Violation Data:")
    print(f"{result}\n")
    print(f"{'=' * 80}")
    print("REMEDIATION ANALYSIS:")
    print(f"{'=' * 80}\n")

    analysis = checker.analyze_failed_assertion(assertion, result)

    print("\n" + "=" * 80)

# Clean up
checker.close()
print("\n[INFO] Compliance checker closed successfully.")
