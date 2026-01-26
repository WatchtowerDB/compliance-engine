"""
GOLD STANDARD TEST DATASET FOR ANALYSIS QUALITY
"""

from .ground_truth import GroundTruth
from .test_case import TestCase


def create_analysis_quality_test_dataset() -> list[TestCase]:
    """
    Create test cases for evaluating remediation analysis quality.

    Each test case represents a failed assertion with expected analysis content.

    Returns:
        List of TestCase objects
    """

    test_cases = []

    # ! THE FOLLOWING TEST CASES ARE AI GENERATED. THEY MAY NOT BE ACCURATE.
    # ! CHECK, REMOVE, OR REFINE THEM AFTER THE TEST SUITE IS FUNCTIONAL.
    # Test Case 1: CVV Storage Violation
    test_cases.append(
        TestCase(
            name="TC001_CVV_Storage_Analysis",
            description="Analysis quality for CVV storage violation",
            failed_assertion="SELECT * FROM customers WHERE cvv IS NOT NULL",
            failure_result="id: 1, cvv: 123\nid: 2, cvv: 456\nid: 3, cvv: 789",
            schema_context="""
        CREATE TABLE customers (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            cvv VARCHAR(4)
        );
        """,
            ground_truth=GroundTruth(
                violation_description="CVV storage (prohibited)",
                pci_requirement="Req 3.4",
                required_elements={
                    "CVV",
                    "CVC",
                    "prohibited",
                    "sensitive authentication data",
                    "requirement 3.4",
                    "never store",
                },
                key_phrases=[
                    "sensitive authentication data",
                    "card verification value",
                    "prohibited after authorization",
                    "security risk",
                    "counterfeit cards",
                ],
                remediation_steps=[
                    "Remove CVV column from database",
                    "Delete all stored CVV values",
                    "Update application to not store CVV",
                    "Implement validation to reject CVV storage",
                ],
                sql_fix_required=True,
            ),
        )
    )

    # Test Case 2: Unencrypted PAN
    test_cases.append(
        TestCase(
            name="TC002_Unencrypted_PAN_Analysis",
            description="Analysis quality for unencrypted PAN storage",
            failed_assertion="SELECT * FROM transactions WHERE card_number IS NOT NULL AND card_number NOT LIKE '%encrypted%'",
            failure_result="transaction_id: 101, card_number: 4532123456789012\ntransaction_id: 102, card_number: 5425233430109903",
            schema_context="""
        CREATE TABLE transactions (
            transaction_id INT PRIMARY KEY,
            card_number VARCHAR(19),
            amount DECIMAL(10, 2)
        );
        """,
            ground_truth=GroundTruth(
                violation_description="Unencrypted PAN storage",
                pci_requirement="Req 3.5.1",
                required_elements={
                    "PAN",
                    "Primary Account Number",
                    "encryption",
                    "requirement 3.5.1",
                    "cardholder data",
                    "plaintext",
                },
                key_phrases=[
                    "unencrypted",
                    "stored in plaintext",
                    "strong cryptography",
                    "AES-256",
                    "data breach risk",
                    "render cardholder data unreadable",
                ],
                remediation_steps=[
                    "Encrypt card_number column using AES-256",
                    "Implement encryption key management",
                    "Store only last 4 digits in plaintext",
                    "Consider tokenization as alternative",
                ],
                sql_fix_required=True,
            ),
        )
    )

    # Test Case 3: Track Data Storage
    test_cases.append(
        TestCase(
            name="TC003_Track_Data_Analysis",
            description="Analysis quality for track data violation",
            failed_assertion="SELECT * FROM card_swipes WHERE track1_data IS NOT NULL OR track2_data IS NOT NULL",
            failure_result="id: 5, track1_data: %B4532...^DOE/JOHN^..., track2_data: 4532...",
            schema_context="""
        CREATE TABLE card_swipes (
            id INT PRIMARY KEY,
            track1_data VARCHAR(256),
            track2_data VARCHAR(256)
        );
        """,
            ground_truth=GroundTruth(
                violation_description="Track data storage (prohibited)",
                pci_requirement="Req 3.4",
                required_elements={
                    "track data",
                    "magnetic stripe",
                    "requirement 3.4",
                    "prohibited",
                    "sensitive authentication data",
                },
                key_phrases=[
                    "track 1",
                    "track 2",
                    "full magnetic stripe",
                    "never store after authorization",
                    "counterfeit card creation",
                ],
                remediation_steps=[
                    "Drop track1_data and track2_data columns",
                    "Delete all track data immediately",
                    "Update card readers to not store track data",
                    "Implement point-to-point encryption",
                ],
                sql_fix_required=True,
            ),
        )
    )

    # Test Case 4: Missing Audit Logging
    test_cases.append(
        TestCase(
            name="TC004_Missing_Audit_Log_Analysis",
            description="Analysis quality for missing audit timestamps",
            failed_assertion="SELECT table_name FROM information_schema.tables WHERE table_name = 'customer_payments' AND table_name NOT IN (SELECT table_name FROM information_schema.columns WHERE column_name IN ('created_at', 'updated_at'))",
            failure_result="table_name: customer_payments",
            schema_context="""
        CREATE TABLE customer_payments (
            id INT PRIMARY KEY,
            customer_id INT,
            pan_hash VARCHAR(64),
            amount DECIMAL(10, 2)
        );
        """,
            ground_truth=GroundTruth(
                violation_description="Missing audit timestamps",
                pci_requirement="Req 10.2",
                required_elements={
                    "audit",
                    "logging",
                    "timestamp",
                    "requirement 10.2",
                    "access tracking",
                    "accountability",
                },
                key_phrases=[
                    "audit trail",
                    "log all access",
                    "who accessed what when",
                    "forensic investigation",
                    "compliance monitoring",
                ],
                remediation_steps=[
                    "Add created_at timestamp column",
                    "Add updated_at timestamp column",
                    "Add modified_by user tracking column",
                    "Implement triggers to auto-update timestamps",
                    "Create dedicated audit log table",
                ],
                sql_fix_required=True,
            ),
        )
    )

    # Test Case 5: Unrestricted Access
    test_cases.append(
        TestCase(
            name="TC005_Public_Access_Analysis",
            description="Analysis quality for public access violation",
            failed_assertion="SELECT grantee, table_name FROM information_schema.table_privileges WHERE table_name = 'card_data' AND grantee = 'PUBLIC'",
            failure_result="grantee: PUBLIC, table_name: card_data",
            schema_context="""
        CREATE TABLE card_data (
            id INT PRIMARY KEY,
            pan_encrypted VARBINARY(256)
        );
        GRANT ALL PRIVILEGES ON card_data TO PUBLIC;
        """,
            ground_truth=GroundTruth(
                violation_description="Public access to cardholder data",
                pci_requirement="Req 7.1.2",
                required_elements={
                    "access control",
                    "PUBLIC",
                    "requirement 7.1.2",
                    "least privilege",
                    "need-to-know",
                },
                key_phrases=[
                    "overly permissive",
                    "role-based access control",
                    "need-to-know basis",
                    "unauthorized access",
                    "data exposure",
                ],
                remediation_steps=[
                    "Revoke PUBLIC access immediately",
                    "Create specific roles for cardholder data access",
                    "Grant access only to authorized users",
                    "Implement RBAC with minimal privileges",
                    "Document access justification",
                ],
                sql_fix_required=True,
            ),
        )
    )

    return test_cases
