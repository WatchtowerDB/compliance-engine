"""
GOLD STANDARD TEST DATASET FOR ANALYSIS QUALITY
"""

from .ground_truth import GroundTruth
from .synonym_set import SynonymSet
from .test_case import TestCase


def create_analysis_quality_test_dataset() -> list[TestCase]:
    """
    Create test cases for evaluating remediation analysis quality.

    Each test case represents a failed assertion with expected analysis content.

    Returns:
        List of TestCase objects
    """

    test_cases = []

    # ==================== REQUIREMENT 3: Protect Stored Account Data ====================
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
                pci_requirements=["Req 3.2", "Req 3.3"],
                required_phrases={
                    SynonymSet("CVV", "card verification value", "CVC"),
                    SynonymSet("prohibited", "not allowed", "limited", "not stored"),
                    SynonymSet(
                        "SAD",
                        "Sensitive Authentication Data",
                        "Sensitive Cardholder Data",
                    ),
                },
                preferred_phrases=[
                    "need to know",
                    SynonymSet("counterfeit payment cards", "counterfeit cards"),
                    "fraudulent transactions",
                    SynonymSet("encrypt", "plaintext", "cleartext", "unencrypt"),
                ],
                remediation_steps=[
                    SynonymSet(
                        "Remove CVV column / data from database",
                        "Drop CVV column / data from database",
                        "Delete CVV column / data from database",
                    ),
                    SynonymSet("Implement Access Controls", "Verifiy Access Controls"),
                    SynonymSet(
                        "Document Policies and Business Justification",
                        "Review Policies and Business Justification",
                    ),
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
            failed_assertion=r"SELECT * FROM transactions WHERE card_number IS NOT NULL AND card_number NOT LIKE '%encrypted%'",
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
                pci_requirements=["Req 3.5"],
                required_phrases={
                    SynonymSet("PAN", "Primary Account Number"),
                    SynonymSet(
                        "encrypt", "plaintext", "cryptography", "unecrypt", "cleartext"
                    ),
                    "hash",
                },
                preferred_phrases=[
                    SynonymSet("defense in depth", "defense-in-depth"),
                    SynonymSet("4 digit", "4-digit", "four digit", "four-digit"),
                    "reconstruct",
                    "data breach",
                    "unreadable",
                ],
                remediation_steps=[
                    SynonymSet(
                        "Encrypt card_number column using AES-256",
                        "Encrypt card number column using AES-256",
                    ),
                    SynonymSet(
                        "Implement encryption key management",
                        "Implement encryption key-management",
                    ),
                    SynonymSet(
                        "Remove Plaintext Data",
                        "Drop Plaintext Data",
                        "Delete Plaintext Data",
                    ),
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
                pci_requirements=["Req 3.3.1"],
                required_phrases={
                    SynonymSet("full track", "track 1", "track 2"),
                    SynonymSet("prohibited", "not allowed", "limited", "not stored"),
                    SynonymSet(
                        "SAD",
                        "Sensitive Authentication Data",
                        "Sensitive Cardholder Data",
                    ),
                },
                preferred_phrases=[
                    SynonymSet("magnetic stripe", "magnetic-stripe", "chip"),
                    SynonymSet(
                        "reproduce payment card",
                        "reproduce card",
                        "counterfeit card",
                        "counterfeit payment card",
                    ),
                    "fraudulent transaction",
                ],
                remediation_steps=[
                    SynonymSet(
                        "Remove track1_data and track2_data columns",
                        "Remove track 1 data and track 2 data columns",
                        "Drop track1_data and track2_data columns",
                        "Drop track 1 data and track 2 data columns",
                        "Delete track1_data and track2_data columns",
                        "Delete track 1 data and track 2 data columns",
                    ),
                    SynonymSet(
                        "Delete all track data",
                        "Remove all track data",
                        "Drop all track data",
                    ),
                    SynonymSet(
                        "Ensure data deletion after authorization",
                        "Ensure data removal after authorization",
                    ),
                ],
                sql_fix_required=True,
            ),
        )
    )

    # ==================== REQUIREMENT 4: Protect Cardholder Data with Strong Cryptography During Transmission Over Open, Public Networks ====================

    # Test Case 4: Unencrypted Transmission Indicators
    test_cases.append(
        TestCase(
            name="TC004_Unencrypted_Transmission_Analysis",
            description="Analysis quality for unencrypted data transmission indicators",
            failed_assertion="SELECT * FROM api_configs WHERE endpoint LIKE 'http://%' AND endpoint NOT LIKE 'http://localhost%'",
            failure_result="config_id: 1, endpoint: http://payment-gateway.petstore.com/process\nconfig_id: 2, endpoint: http://api.vendor.com/card-data",
            schema_context="""
        CREATE TABLE api_configs (
            config_id INT PRIMARY KEY,
            endpoint VARCHAR(255),
            service_name VARCHAR(100)
        );
        """,
            ground_truth=GroundTruth(
                violation_description="Unencrypted transmission of PAN",
                pci_requirements=["Req 4.2"],
                required_phrases={
                    SynonymSet("transmission", "transmit", "transit", "transfer"),
                    SynonymSet("TLS", "SSL", "TSL/SSL", "HTTPS"),
                    SynonymSet("encrypt", "encryption", "encrypted", "cryptography"),
                },
                preferred_phrases=[
                    SynonymSet("strong cryptography", "robust cryptography"),
                    SynonymSet("open", "public", "untrusted"),
                    "data breach",
                    SynonymSet(
                        "man-in-the-middle",
                        "MITM",
                        "interception",
                        "intercept",
                        "tamper",
                    ),
                    SynonymSet("eavesdropping", "eavesdrop", "sniffing"),
                    SynonymSet("open network", "public network", "untrusted network"),
                ],
                remediation_steps=[
                    SynonymSet(
                        "Update endpoints to use HTTPS",
                        "Migrate endpoints to HTTPS",
                        "Change endpoints to HTTPS",
                    ),
                    SynonymSet(
                        "Encrypt data at the session level",
                        "Implement TLS 1.3",
                        "Use TLS 1.3",
                        "Enable TLS 1.3",
                        "Implement TLS 1.2 or higher",
                        "Use TLS 1.2 or higher",
                        "Enable TLS 1.2 or higher",
                        "Implement TLS/SSL",
                        "Use TLS/SSL",
                        "Enable TLS/SSL",
                    ),
                    SynonymSet(
                        "Validate certificate configuration",
                        "Verify certificate configuration",
                        "Review certificate configuration",
                    ),
                ],
                sql_fix_required=False,
            ),
        )
    )

    # ==================== REQUIREMENT 7: Requirement 7: Restrict Access to System Components and Cardholder Data by Business Need to Know ====================

    # Test Case 5: Missing Access Controls
    test_cases.append(
        TestCase(
            name="TC005_Missing_Access_Controls_Analysis",
            description="Analysis quality for missing access control mechanisms",
            failed_assertion="SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('payments', 'credit_cards', 'customer_cards') AND table_name NOT IN (SELECT table_name FROM information_schema.table_privileges WHERE grantee != 'PUBLIC')",
            failure_result="table_name: payments\ntable_name: credit_cards",
            schema_context="""
        CREATE TABLE payments (
            payment_id INT PRIMARY KEY,
            card_number VARCHAR(19),
            amount DECIMAL(10, 2)
        );

        CREATE TABLE credit_cards (
            card_id INT PRIMARY KEY,
            pan VARCHAR(19),
            cardholder_name VARCHAR(100)
        );
        """,
            ground_truth=GroundTruth(
                violation_description="Unrestricted access to cardholder data",
                pci_requirements=["Req 7.2", "Req 7.3"],
                required_phrases={
                    SynonymSet("access control", "access restriction", "authorization"),
                    SynonymSet(
                        "need to know",
                        "need-to-know",
                        "business need",
                        "business-need",
                        "access need",
                        "access-need",
                    ),
                    SynonymSet(
                        "least privilege",
                        "least-privilege",
                        "minimum privilege",
                        "minimum necessary",
                    ),
                },
                preferred_phrases=[
                    SynonymSet(
                        "separation of duties",
                        "separation-of-duties",
                        "separationof duty",
                        "separation-of-duty",
                    ),
                    SynonymSet(
                        "role based",
                        "role-based",
                        "RBAC",
                        "attribute based",
                        "attribute-based",
                        "ABAC",
                    ),
                    SynonymSet(
                        "authorized personnel",
                        "authorized users",
                        "authorized individuals",
                    ),
                    "job function",
                    "data breach",
                ],
                remediation_steps=[
                    SynonymSet(
                        "Implement role-based access control / RBAC",
                        "Configure role-based access control / RBAC",
                        "Establish role-based access control / RBAC",
                        "Implement attribute-based access control / ABAC",
                        "Configure attribute-based access control / ABAC",
                        "Establish attribute-based access control / ABAC",
                    ),
                    SynonymSet(
                        "Define user roles and permissions",
                        "Create user roles and permissions",
                        "Establish user roles and permissions",
                    ),
                    SynonymSet(
                        "Restrict access to authorized personnel only",
                        "Limit access to authorized personnel only",
                        "Revoke public access",
                    ),
                ],
                sql_fix_required=True,
            ),
        )
    )

    # ! THE FOLLOWING TEST CASES ARE AI GENERATED. THEY MAY NOT BE ACCURATE.
    # ! CHECK, REMOVE, OR REFINE THEM AFTER THE TEST SUITE IS FUNCTIONAL.

    # # # Test Case 6: Overly Permissive Access
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC006_Overly_Permissive_Access_Analysis",
    # #         description="Analysis quality for overly broad access permissions",
    # #         failed_assertion="SELECT user_name, privilege_type FROM user_privileges WHERE privilege_type IN ('ALL', 'SUPER', 'GRANT') AND table_name IN ('cardholder_data', 'transactions', 'payment_info')",
    # #         failure_result="user_name: app_user, privilege_type: ALL\nuser_name: reporting_user, privilege_type: ALL",
    # #         schema_context="""
    # #     CREATE TABLE user_privileges (
    # #         privilege_id INT PRIMARY KEY,
    # #         user_name VARCHAR(100),
    # #         table_name VARCHAR(100),
    # #         privilege_type VARCHAR(50)
    # #     );

    # #     CREATE TABLE cardholder_data (
    # #         customer_id INT PRIMARY KEY,
    # #         pan VARCHAR(19),
    # #         expiration_date VARCHAR(7)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Excessive privileges granted for cardholder data access",
    # #             pci_requirements=["Req 7.2.2", "Req 7.2.4"],
    # #             required_phrases={
    # #                 SynonymSet(
    # #                     "least privilege", "minimum privilege", "minimum necessary"
    # #                 ),
    # #                 SynonymSet("need to know", "need-to-know", "business need"),
    # #                 SynonymSet("job function", "job role", "business function"),
    # #             },
    # #             preferred_phrases=[
    # #                 "excessive privilege",
    # #                 SynonymSet("granular", "specific", "limited"),
    # #                 "privilege escalation",
    # #                 SynonymSet("segregation of duties", "separation of duties"),
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Review and reduce user privileges",
    # #                     "Audit and reduce user privileges",
    # #                     "Revoke excessive privileges",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Grant only necessary permissions",
    # #                     "Assign only necessary permissions",
    # #                     "Provide minimum required permissions",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Implement principle of least privilege",
    # #                     "Apply principle of least privilege",
    # #                     "Enforce principle of least privilege",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    # # # ==================== REQUIREMENT 8: AUTHENTICATION ====================

    # # # Test Case 7: Weak Password Storage
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC007_Weak_Password_Storage_Analysis",
    # #         description="Analysis quality for weak password hashing",
    # #         failed_assertion="SELECT user_id, username FROM users WHERE password_hash IS NOT NULL AND (LENGTH(password_hash) < 32 OR password_hash NOT LIKE '%$%')",
    # #         failure_result="user_id: 100, username: admin\nuser_id: 101, username: cashier1",
    # #         schema_context="""
    # #     CREATE TABLE users (
    # #         user_id INT PRIMARY KEY,
    # #         username VARCHAR(100),
    # #         password_hash VARCHAR(255),
    # #         access_level VARCHAR(50)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Weak or inadequate password hashing",
    # #             pci_requirements=["Req 8.3.2", "Req 8.3.6"],
    # #             required_phrases={
    # #                 SynonymSet("hash", "hashing", "cryptographic hash"),
    # #                 SynonymSet("salt", "salted", "salting"),
    # #                 SynonymSet("one-way", "irreversible", "non-reversible"),
    # #             },
    # #             preferred_phrases=[
    # #                 SynonymSet("bcrypt", "PBKDF2", "scrypt", "Argon2"),
    # #                 SynonymSet(
    # #                     "strong hash", "secure hash", "cryptographic hash function"
    # #                 ),
    # #                 "password security",
    # #                 "authentication credential",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Implement strong password hashing algorithm",
    # #                     "Use strong password hashing algorithm",
    # #                     "Apply strong password hashing algorithm",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Use bcrypt, PBKDF2, or Argon2",
    # #                     "Implement bcrypt, PBKDF2, or Argon2",
    # #                     "Migrate to bcrypt, PBKDF2, or Argon2",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Apply salt to password hashes",
    # #                     "Include salt in password hashes",
    # #                     "Add salt to password hashing",
    # #                 ),
    # #             ],
    # #             sql_fix_required=False,
    # #         ),
    # #     )
    # # )

    # # # Test Case 8: Missing Multi-Factor Authentication Tracking
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC008_Missing_MFA_Tracking_Analysis",
    # #         description="Analysis quality for missing MFA implementation tracking",
    # #         failed_assertion="SELECT u.user_id, u.username, u.access_level FROM users u WHERE u.access_level IN ('admin', 'privileged') AND NOT EXISTS (SELECT 1 FROM authentication_methods am WHERE am.user_id = u.user_id AND am.method_type = 'MFA')",
    # #         failure_result="user_id: 200, username: db_admin, access_level: admin\nuser_id: 201, username: security_admin, access_level: admin",
    # #         schema_context="""
    # #     CREATE TABLE users (
    # #         user_id INT PRIMARY KEY,
    # #         username VARCHAR(100),
    # #         access_level VARCHAR(50)
    # #     );

    # #     CREATE TABLE authentication_methods (
    # #         method_id INT PRIMARY KEY,
    # #         user_id INT,
    # #         method_type VARCHAR(50)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Missing multi-factor authentication for privileged access",
    # #             pci_requirements=["Req 8.4.2", "Req 8.4.3", "Req 8.5.1"],
    # #             required_phrases={
    # #                 SynonymSet(
    # #                     "multi-factor",
    # #                     "MFA",
    # #                     "two-factor",
    # #                     "2FA",
    # #                     "multiple authentication",
    # #                 ),
    # #                 SynonymSet(
    # #                     "privileged access", "administrative access", "admin access"
    # #                 ),
    # #                 SynonymSet("authentication factor", "authentication method"),
    # #             },
    # #             preferred_phrases=[
    # #                 SynonymSet(
    # #                     "something you know", "something you have", "something you are"
    # #                 ),
    # #                 "credential compromise",
    # #                 SynonymSet("unauthorized access", "unauthorized entry"),
    # #                 "authentication mechanism",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Implement multi-factor authentication for privileged users",
    # #                     "Enable multi-factor authentication for privileged users",
    # #                     "Configure multi-factor authentication for privileged users",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Track MFA enrollment in database",
    # #                     "Record MFA enrollment in database",
    # #                     "Store MFA enrollment in database",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Enforce MFA for administrative access",
    # #                     "Require MFA for administrative access",
    # #                     "Mandate MFA for administrative access",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    # # # Test Case 9: Default Credentials
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC009_Default_Credentials_Analysis",
    # #         description="Analysis quality for default or weak credentials",
    # #         failed_assertion="SELECT user_id, username FROM users WHERE username IN ('admin', 'root', 'administrator', 'default') OR password_hash = 'e10adc3949ba59abbe56e057f20f883e'",
    # #         failure_result="user_id: 1, username: admin\nuser_id: 2, username: root",
    # #         schema_context="""
    # #     CREATE TABLE users (
    # #         user_id INT PRIMARY KEY,
    # #         username VARCHAR(100),
    # #         password_hash VARCHAR(255),
    # #         created_at TIMESTAMP
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Default or vendor-supplied credentials in use",
    # #             pci_requirements=["Req 8.3.6", "Req 2.2.2"],
    # #             required_phrases={
    # #                 SynonymSet(
    # #                     "default credential",
    # #                     "vendor-supplied credential",
    # #                     "default password",
    # #                 ),
    # #                 SynonymSet("change", "replace", "remove"),
    # #                 SynonymSet("unique", "custom", "organization-specific"),
    # #             },
    # #             preferred_phrases=[
    # #                 "vendor default",
    # #                 SynonymSet("well-known", "publicly known", "commonly known"),
    # #                 "credential compromise",
    # #                 "security hardening",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Change all default credentials",
    # #                     "Replace all default credentials",
    # #                     "Remove all default credentials",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Implement strong unique passwords",
    # #                     "Create strong unique passwords",
    # #                     "Establish strong unique passwords",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Document password change procedures",
    # #                     "Establish password change procedures",
    # #                     "Create password change procedures",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    # # # ==================== REQUIREMENT 10: LOGGING AND MONITORING ====================

    # # # Test Case 10: Missing Audit Timestamps
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC010_Missing_Audit_Timestamps_Analysis",
    # #         description="Analysis quality for missing audit trail timestamps",
    # #         failed_assertion="SELECT table_name FROM information_schema.tables WHERE table_name IN ('payments', 'transactions', 'cardholder_data') AND table_name NOT IN (SELECT table_name FROM information_schema.columns WHERE column_name IN ('created_at', 'updated_at', 'modified_at', 'timestamp'))",
    # #         failure_result="table_name: payments\ntable_name: cardholder_data",
    # #         schema_context="""
    # #     CREATE TABLE payments (
    # #         payment_id INT PRIMARY KEY,
    # #         card_number VARCHAR(19),
    # #         amount DECIMAL(10, 2)
    # #     );

    # #     CREATE TABLE cardholder_data (
    # #         customer_id INT PRIMARY KEY,
    # #         pan VARCHAR(19),
    # #         cvv VARCHAR(4)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Missing audit trail timestamps for cardholder data access",
    # #             pci_requirements=["Req 10.2", "Req 10.2.1", "Req 10.3"],
    # #             required_phrases={
    # #                 SynonymSet("audit trail", "audit log", "audit record"),
    # #                 SynonymSet("timestamp", "time stamp", "date and time"),
    # #                 SynonymSet("track", "record", "log", "capture"),
    # #             },
    # #             preferred_phrases=[
    # #                 SynonymSet("created_at", "updated_at", "modified_at"),
    # #                 "chronological order",
    # #                 SynonymSet(
    # #                     "forensic analysis",
    # #                     "security investigation",
    # #                     "incident investigation",
    # #                 ),
    # #                 "accountability",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Add timestamp columns to tables",
    # #                     "Create timestamp columns in tables",
    # #                     "Include timestamp columns in tables",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Implement automatic timestamp tracking",
    # #                     "Enable automatic timestamp tracking",
    # #                     "Configure automatic timestamp tracking",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Use created_at and updated_at fields",
    # #                     "Add created_at and updated_at fields",
    # #                     "Include created_at and updated_at fields",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    # # # Test Case 11: Missing User Tracking
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC011_Missing_User_Tracking_Analysis",
    # #         description="Analysis quality for missing user identification in audit logs",
    # #         failed_assertion="SELECT table_name FROM information_schema.tables WHERE table_name IN ('payment_transactions', 'card_updates', 'data_access_log') AND table_name NOT IN (SELECT table_name FROM information_schema.columns WHERE column_name IN ('user_id', 'modified_by', 'created_by', 'actor_id'))",
    # #         failure_result="table_name: payment_transactions\ntable_name: card_updates",
    # #         schema_context="""
    # #     CREATE TABLE payment_transactions (
    # #         transaction_id INT PRIMARY KEY,
    # #         card_number VARCHAR(19),
    # #         amount DECIMAL(10, 2),
    # #         transaction_date TIMESTAMP
    # #     );

    # #     CREATE TABLE card_updates (
    # #         update_id INT PRIMARY KEY,
    # #         card_id INT,
    # #         field_changed VARCHAR(100),
    # #         new_value VARCHAR(255)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Missing user identification in audit trails",
    # #             pci_requirements=["Req 10.2.2", "Req 10.3.2"],
    # #             required_phrases={
    # #                 SynonymSet("user identification", "user identity", "user ID"),
    # #                 SynonymSet("individual", "user", "person", "actor"),
    # #                 SynonymSet("accountability", "attribution", "traceability"),
    # #             },
    # #             preferred_phrases=[
    # #                 SynonymSet("modified_by", "created_by", "user_id", "actor_id"),
    # #                 "access event",
    # #                 SynonymSet("forensic", "investigation", "audit"),
    # #                 "non-repudiation",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Add user identification columns",
    # #                     "Create user identification columns",
    # #                     "Include user identification columns",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Track user actions on cardholder data",
    # #                     "Record user actions on cardholder data",
    # #                     "Log user actions on cardholder data",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Implement user attribution mechanism",
    # #                     "Enable user attribution mechanism",
    # #                     "Configure user attribution mechanism",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    # # # Test Case 12: No Access Logging
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC012_No_Access_Logging_Analysis",
    # #         description="Analysis quality for missing access logging mechanism",
    # #         failed_assertion="SELECT 'No access log table found' AS violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name IN ('access_log', 'audit_log', 'security_log', 'cardholder_access_log'))",
    # #         failure_result="violation: No access log table found",
    # #         schema_context="""
    # #     CREATE TABLE customers (
    # #         customer_id INT PRIMARY KEY,
    # #         name VARCHAR(100)
    # #     );

    # #     CREATE TABLE credit_cards (
    # #         card_id INT PRIMARY KEY,
    # #         customer_id INT,
    # #         pan VARCHAR(19),
    # #         expiration_date VARCHAR(7)
    # #     );

    # #     CREATE TABLE transactions (
    # #         transaction_id INT PRIMARY KEY,
    # #         card_id INT,
    # #         amount DECIMAL(10, 2)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="No audit logging mechanism for cardholder data access",
    # #             pci_requirements=["Req 10.2", "Req 10.2.1", "Req 10.4"],
    # #             required_phrases={
    # #                 SynonymSet("audit log", "access log", "security log"),
    # #                 SynonymSet("log", "record", "track", "capture"),
    # #                 SynonymSet("access to cardholder data", "cardholder data access"),
    # #             },
    # #             preferred_phrases=[
    # #                 SynonymSet("log entry", "audit record", "log event"),
    # #                 "security event",
    # #                 SynonymSet("monitoring", "detection", "alerting"),
    # #                 "system activity",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Create audit log table",
    # #                     "Implement audit log table",
    # #                     "Establish audit log table",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Log all access to cardholder data",
    # #                     "Record all access to cardholder data",
    # #                     "Track all access to cardholder data",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Include user, timestamp, action, and affected data",
    # #                     "Capture user, timestamp, action, and affected data",
    # #                     "Record user, timestamp, action, and affected data",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    # # # Test Case 13: Insufficient Logging Detail
    # # test_cases.append(
    # #     TestCase(
    # #         name="TC013_Insufficient_Logging_Detail_Analysis",
    # #         description="Analysis quality for insufficient audit log detail",
    # #         failed_assertion="SELECT 'Insufficient logging' AS violation FROM information_schema.tables t WHERE t.table_name = 'audit_log' AND (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = 'audit_log' AND c.column_name IN ('event_type', 'user_id', 'timestamp', 'affected_resource', 'action_taken', 'outcome')) < 5",
    # #         failure_result="violation: Insufficient logging",
    # #         schema_context="""
    # #     CREATE TABLE audit_log (
    # #         log_id INT PRIMARY KEY,
    # #         timestamp TIMESTAMP,
    # #         user_id INT
    # #     );

    # #     CREATE TABLE cardholder_data (
    # #         customer_id INT PRIMARY KEY,
    # #         pan VARCHAR(19),
    # #         cardholder_name VARCHAR(100)
    # #     );
    # #     """,
    # #         ground_truth=GroundTruth(
    # #             violation_description="Insufficient detail in audit logs",
    # #             pci_requirements=[
    # #                 "Req 10.3",
    # #                 "Req 10.3.1",
    # #                 "Req 10.3.2",
    # #                 "Req 10.3.3",
    # #                 "Req 10.3.4",
    # #             ],
    # #             required_phrases={
    # #                 SynonymSet("audit log detail", "log detail", "logging detail"),
    # #                 SynonymSet("event type", "action", "activity"),
    # #                 SynonymSet("outcome", "result", "success or failure"),
    # #             },
    # #             preferred_phrases=[
    # #                 SynonymSet("affected resource", "data element", "system component"),
    # #                 "event correlation",
    # #                 SynonymSet("forensic analysis", "incident investigation"),
    # #                 "audit trail completeness",
    # #             ],
    # #             remediation_steps=[
    # #                 SynonymSet(
    # #                     "Add required audit log fields",
    # #                     "Include required audit log fields",
    # #                     "Implement required audit log fields",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Capture event type, timestamp, user, resource, action, and outcome",
    # #                     "Record event type, timestamp, user, resource, action, and outcome",
    # #                     "Log event type, timestamp, user, resource, action, and outcome",
    # #                 ),
    # #                 SynonymSet(
    # #                     "Ensure comprehensive audit trail",
    # #                     "Maintain comprehensive audit trail",
    # #                     "Establish comprehensive audit trail",
    # #                 ),
    # #             ],
    # #             sql_fix_required=True,
    # #         ),
    # #     )
    # # )

    return test_cases
