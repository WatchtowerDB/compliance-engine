#!/usr/bin/env python3

import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from .models.download_model import download_model
from .scripts.pci_compliance_checker import PCIComplianceChecker

SCRIPT_DIR = Path(__file__).parent
MODEL_PATH: Path = Path(
    os.getenv(
        "WTCE_MODEL_PATH",
        SCRIPT_DIR.parent.parent.parent
        / "models/base/Ministral-8B-Instruct-2410-GGUF/Ministral-8B-Instruct-2410-Q6_K_L.gguf",
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

# Initialize the PCI compliance checker
checker = PCIComplianceChecker(
    model_path=MODEL_PATH, chroma_dir=CHROMA_DIR, collection_name="PCI-DSS-v4.0.1"
)

assertions = [
    "SELECT * FROM operations.cardholder_data WHERE card_number NOT LIKE '%%%%'",
    "SELECT * FROM operations.transactions WHERE sad_data IS NOT NULL OR full_pan IS NOT NULL",
    "SELECT * FROM operations.cardholder_data WHERE cvv IS NOT NULL",
    "SELECT * FROM operations.audit_logs WHERE event_timestamp IS NULL OR user_id IS NULL OR event_type IS NULL OR data_accessed IS NULL",
    "SELECT * FROM operations.users WHERE can_view_full_pan = true AND requires_full_pan = false OR access_approved = false",
    "SELECT * FROM operations.transactions WHERE authorization_code IS NOT NULL AND response_code IS NOT NULL AND sad_data IS NOT NULL",
    "SELECT * FROM operations.cardholder_data WHERE card_number_masked IS NULL OR card_number_masked != card_number",
    "SELECT * FROM operations.transactions WHERE full_pan IS NOT NULL AND (card_number_masked IS NULL OR card_number_masked != full_pan)",
]

DB_CONFIG = {
    "dbname": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "host": "localhost",
    "port": "5432",
}

failed_assertions = {}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print(
        f"[INFO] Connected to database '{DB_CONFIG['dbname']}' at {DB_CONFIG['host']}:{DB_CONFIG['port']}"
    )

    for i, assertion in enumerate(assertions, 1):
        print(f"\nRunning Assertion {i}...")
        try:
            cur.execute(assertion)
            rows = cur.fetchall()
            if rows:
                print(f"  [FAIL] Violation detected! {len(rows)} records found.")
                # Format result for analysis
                result_str = "\n".join([str(dict(row)) for row in rows[:5]])
                if len(rows) > 5:
                    result_str += f"\n... and {len(rows) - 5} more records."
                failed_assertions[assertion] = result_str
            else:
                print("  [PASS] No violations found.")
        except psycopg2.Error as e:
            print(f"  [ERROR] Database error: {e}")
            conn.rollback()

    cur.close()
    conn.close()
except Exception as e:
    print(f"[ERROR] Database connection failed: {e}")
    print("Ensure your Docker container is running: docker-compose up -d")


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
