from ...benchmark_case import BenchmarkCase
from ...ground_truth import AssertionAnalysisGroundTruth
from ...synonym_set import SynonymSet

PCI_DSS_STAGE_4_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        name="PCI_DSS_ST4_TC001_CVV_Storage_Analysis",
        description="Stage 4: analysis quality for CVV storage violation",
        schema="""
            CREATE TABLE customers (
                id INT PRIMARY KEY,
                name VARCHAR(100),
                cvv VARCHAR(4)
            );
            """,
        failed_assertion="SELECT * FROM customers WHERE cvv IS NOT NULL",
        failure_result="id: 1, cvv: 123\nid: 2, cvv: 456\nid: 3, cvv: 789",
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="CVV storage (prohibited)",
            standard_requirements=["Req 3.2", "Req 3.3"],
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
                SynonymSet(
                    "need to know",
                    "need-to-know",
                    "business need",
                    "business-need",
                    "access need",
                    "access-need",
                ),
                SynonymSet("counterfeit payment cards", "counterfeit cards"),
                "fraudulent transaction",
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
        ),
    ),
    # TC002 — Stage 4: Unencrypted PAN analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC002_Unencrypted_PAN_Analysis",
        description="Stage 4: analysis quality for unencrypted PAN storage",
        schema="""
            CREATE TABLE transactions (
                transaction_id INT PRIMARY KEY,
                card_number VARCHAR(19),
                amount DECIMAL(10, 2)
            );
        """,
        failed_assertion=(
            "SELECT * FROM transactions "
            "WHERE card_number IS NOT NULL AND card_number NOT LIKE '%encrypted%'"
        ),
        failure_result=(
            "transaction_id: 101, card_number: 4532123456789012\n"
            "transaction_id: 102, card_number: 5425233430109903"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Unencrypted PAN storage",
            standard_requirements=["Req 3.5"],
            required_phrases={
                SynonymSet("PAN", "Primary Account Number"),
                SynonymSet(
                    "encrypt", "plaintext", "cryptography", "unecrypt", "cleartext"
                ),
                "unauthorized",
            },
            preferred_phrases=[
                SynonymSet("defense in depth", "defense-in-depth"),
                SynonymSet("4 digit", "4-digit", "four digit", "four-digit"),
                "reconstruct",
                SynonymSet("data breach", "security breach"),
                SynonymSet(
                    "unreadable",
                    "strong cryptography",
                ),
                SynonymSet(
                    "truncation",
                    "truncate",
                    "masking",
                    "tokenization",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Encrypt card_number column using AES-256",
                    "Encrypt card number column using AES-256",
                    "Encrypt PAN using AES-256",
                ),
                SynonymSet(
                    "Implement encryption key management",
                    "Implement encryption key-management",
                    "Use encryption key management",
                    "Use encryption key-management",
                ),
                SynonymSet(
                    "Remove plaintext data",
                    "Drop plaintext data",
                    "Delete plaintext data",
                    "Remove cleartext data",
                    "Drop cleartext data",
                    "Delete cleartext data",
                ),
            ],
        ),
    ),
    # TC003 — Stage 4: Track data analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC003_Track_Data_Analysis",
        description="Stage 4: analysis quality for track data violation",
        schema="""
            CREATE TABLE card_swipes (
                id INT PRIMARY KEY,
                track1_data VARCHAR(256),
                track2_data VARCHAR(256)
            );
        """,
        failed_assertion=(
            "SELECT * FROM card_swipes WHERE track1_data IS NOT NULL OR track2_data IS NOT NULL"
        ),
        failure_result=r"id: 5, track1_data: %B4532...^DOE/JOHN^..., track2_data: 4532...",
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Track data storage (prohibited)",
            standard_requirements=["Req 3.3.1.1"],
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
                SynonymSet(
                    "post-authorization",
                    "after authorization",
                    "after the authorization",
                    "after authorization is complete",
                ),
                "rendered unrecoverable",
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
        ),
    ),
    # ==========================================================================
    # REQUIREMENT 4 — Protect data in transit
    # ==========================================================================
    # TC004 — Stage 4: Unencrypted transmission analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC004_Unencrypted_Transmission_Analysis",
        description="Stage 4: analysis quality for unencrypted data transmission indicators",
        schema="""
            CREATE TABLE api_configs (
                config_id INT PRIMARY KEY,
                endpoint VARCHAR(255),
                service_name VARCHAR(100)
            );
        """,
        failed_assertion=(
            "SELECT * FROM api_configs WHERE endpoint LIKE 'http://%' "
            "AND endpoint NOT LIKE 'http://localhost%'"
        ),
        failure_result=(
            "config_id: 1, endpoint: http://payment-gateway.petstore.com/process\n"
            "config_id: 2, endpoint: http://api.vendor.com/card-data"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Unencrypted transmission of PAN",
            standard_requirements=["Req 4.2"],
            required_phrases={
                SynonymSet("transmission", "transmit", "transit", "transfer"),
                SynonymSet("TLS", "SSL", "TSL/SSL", "HTTPS"),
                SynonymSet("encrypt", "encryption", "encrypted", "cryptography"),
            },
            preferred_phrases=[
                SynonymSet("strong cryptography", "robust cryptography"),
                SynonymSet("open", "public", "untrusted"),
                SynonymSet("data breach", "security breach"),
                SynonymSet(
                    "man-in-the-middle",
                    "MITM",
                    "interception",
                    "intercept",
                    "tamper",
                    "eavesdropping",
                    "eavesdrop",
                    "sniffing",
                ),
                SynonymSet("open network", "public network", "untrusted network"),
                SynonymSet(
                    "certificate validation",
                    "certificate verification",
                    "valid certificates",
                ),
                SynonymSet("loopback", "local network", "localhost"),
                SynonymSet(
                    "secure version",
                    "secure protocol",
                    "secure configuration",
                ),
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
        ),
    ),
    # ==========================================================================
    # REQUIREMENT 7 — Restrict access by business need-to-know
    # ==========================================================================
    # TC005 — Stage 4: Missing access controls analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC005_Missing_Access_Controls_Analysis",
        description="Stage 4: analysis quality for missing access control mechanisms",
        schema="""
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
        failed_assertion=(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name IN ('payments', 'credit_cards', 'customer_cards') "
            "AND table_name NOT IN (SELECT table_name FROM information_schema.table_privileges "
            "WHERE grantee != 'PUBLIC')"
        ),
        failure_result="table_name: payments\ntable_name: credit_cards",
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Unrestricted access to cardholder data",
            standard_requirements=["Req 7.2", "Req 7.3"],
            required_phrases={
                SynonymSet("access control", "access restriction"),
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
                    "separation of duty",
                    "separation-of-duty",
                    "segregation of duties",
                    "segregation-of-duties",
                    "segregation of duty",
                    "segregation-of-duty",
                ),
                SynonymSet(
                    "authorized personnel",
                    "authorized users",
                    "authorized individuals",
                ),
                SynonymSet(
                    "job function",
                    "job classification",
                    "job role",
                    "business function",
                    "minimum access",
                    "minimum level",
                ),
                SynonymSet("data breach", "security breach"),
                SynonymSet(
                    "enforce permissions",
                    "restrict access",
                    "access must be restricted",
                ),
                SynonymSet("`PUBLIC` access", "public access"),
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
        ),
    ),
    # TC006 — Stage 4: Overly permissive access analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC006_Overly_Permissive_Access_Analysis",
        description="Stage 4: analysis quality for overly broad access permissions",
        schema="""
            CREATE TABLE user_privileges (
                privilege_id INT PRIMARY KEY,
                user_name VARCHAR(100),
                table_name VARCHAR(100),
                privilege_type VARCHAR(50)
            );
            CREATE TABLE cardholder_data (
                customer_id INT PRIMARY KEY,
                pan VARCHAR(19),
                expiration_date VARCHAR(7)
            );
        """,
        failed_assertion=(
            "SELECT user_name, privilege_type FROM user_privileges "
            "WHERE privilege_type IN ('ALL', 'SUPER', 'GRANT') "
            "AND table_name IN ('cardholder_data', 'transactions', 'payment_info')"
        ),
        failure_result="[app_user, ALL], [reporting_user, ALL]",
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Excessive privileges granted for cardholder data access",
            standard_requirements=["Req 7.1", "Req 7.2", "Req 7.3"],
            required_phrases={
                SynonymSet("access control", "access restriction"),
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
                SynonymSet(
                    "job function",
                    "job classification",
                    "job role",
                    "business function",
                ),
            },
            preferred_phrases=[
                SynonymSet(
                    "separation of duties",
                    "separation-of-duties",
                    "separation of duty",
                    "separation-of-duty",
                    "segregation of duties",
                    "segregation-of-duties",
                    "segregation of duty",
                    "segregation-of-duty",
                ),
                SynonymSet("data loss", "data breach"),
                "unauthorized",
                SynonymSet(
                    "excessive privileges",
                    "overly permissive access",
                    "broad privileges",
                    "unnecessary privileges",
                    "risk profile",
                ),
                SynonymSet("read access", "write access", "read-only"),
            ],
            remediation_steps=[
                SynonymSet(
                    "Identify job functions and define roles",
                    "Identify job functions and access needs",
                ),
                SynonymSet(
                    "Implement role-based access control / RBAC",
                    "Configure role-based access control / RBAC",
                    "Establish role-based access control / RBAC",
                    "Implement attribute-based access control / ABAC",
                    "Configure attribute-based access control / ABAC",
                    "Establish attribute-based access control / ABAC",
                ),
                SynonymSet(
                    "Adjust privileges to the minimum required",
                    "Provide minimum required permissions",
                    "Update user privileges",
                    "Reduce user privileges",
                    "Limit user privileges",
                    "Modify user privileges",
                    "Review user privileges",
                    "Audit user privileges",
                    "Adjust user privileges",
                    "Revoke excessive privileges",
                    "Grant only necessary permissions",
                    "Assign only necessary permissions",
                ),
            ],
        ),
    ),
    # TC007 — Stage 4: Weak password storage analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC007_Weak_Password_Storage_Analysis",
        description="Stage 4: analysis quality for weak password hashing",
        schema="""
                CREATE TABLE users (
                    user_id INT PRIMARY KEY,
                    username VARCHAR(100),
                    password_hash VARCHAR(255),
                    access_level VARCHAR(50)
                );
            """,
        failed_assertion=(
            "SELECT user_id, username FROM users WHERE password_hash IS NOT NULL "
            "AND (LENGTH(password_hash) < 32 OR password_hash NOT LIKE '%$%')"
        ),
        failure_result="user_id: 100, username: admin\nuser_id: 101, username: cashier1",
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Weak or inadequate password hashing",
            standard_requirements=["Req 8.3", "Req 8.6"],
            required_phrases={
                SynonymSet("hash", "hashing"),
                "authentication",
                SynonymSet("complexity", "complex"),
            },
            preferred_phrases=[
                "factor",
                "characters",
                "minimum",
                SynonymSet("salt", "salted", "salting"),
                SynonymSet("bcrypt", "PBKDF2", "scrypt", "Argon2"),
                SynonymSet(
                    "password policy",
                    "password requirements",
                    "password guidelines",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Generate strong passwords",
                    "Create strong passwords",
                    "Update passwords of affected accounts",
                ),
                SynonymSet(
                    "Implement strong password hashing algorithm",
                    "Use strong password hashing algorithm",
                    "Hash passwords securely",
                ),
                SynonymSet(
                    "Use bcrypt, PBKDF2, or Argon2 hashing implementation",
                    "Migrate to bcrypt, PBKDF2, or Argon2 hashing implementation",
                ),
                SynonymSet(
                    "Apply salt to password hashes",
                    "Include salt in password hashes",
                ),
            ],
        ),
    ),
    # TC008 — Stage 4: Missing MFA tracking analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC008_Missing_MFA_Tracking_Analysis",
        description="Stage 4: analysis quality for missing MFA implementation tracking",
        schema="""
                CREATE TABLE users (
                    user_id INT PRIMARY KEY,
                    username VARCHAR(100),
                    access_level VARCHAR(50)
                );
                CREATE TABLE authentication_methods (
                    method_id INT PRIMARY KEY,
                    user_id INT,
                    method_type VARCHAR(50)
                );
            """,
        failed_assertion=(
            "SELECT u.user_id, u.username, u.access_level FROM users u "
            "WHERE u.access_level IN ('admin', 'privileged') AND NOT EXISTS "
            "(SELECT 1 FROM authentication_methods am WHERE am.user_id = u.user_id "
            "AND am.method_type = 'MFA')"
        ),
        failure_result=(
            "user_id: 200, username: db_admin, access_level: admin\n"
            "user_id: 201, username: security_admin, access_level: admin"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Missing multi-factor authentication for privileged access",
            standard_requirements=["Req 8.4", "Req 8.5.1"],
            required_phrases={
                SynonymSet(
                    "multi-factor",
                    "MFA",
                    "two-factor",
                    "2FA",
                    "multiple authentication",
                ),
                SynonymSet(
                    "privileged access", "administrative access", "admin access"
                ),
                SynonymSet("authentication factor", "authentication method"),
            },
            preferred_phrases=[
                SynonymSet("admin", "escalate", "escalation", "elevation", "elevate"),
                SynonymSet("CDE", "Cardholder Data Environment"),
                SynonymSet(
                    "something you know", "something you have", "something you are"
                ),
                "credentials",
                "unauthorized",
            ],
            remediation_steps=[
                SynonymSet(
                    "Implement multi-factor authentication for privileged users",
                    "Enable multi-factor authentication for privileged users",
                ),
                SynonymSet(
                    "Track MFA enrollment in database",
                    "Record MFA enrollment in database",
                ),
                SynonymSet(
                    "Enforce MFA for privileged / administrative access",
                    "Require MFA for privileged / administrative access",
                ),
            ],
        ),
    ),
    # ==========================================================================
    # REQUIREMENT 10 — Log and monitor all access to system components and CHD
    # ==========================================================================
    # TC009 — Stage 4: Missing/weak security logging analysis
    BenchmarkCase(
        name="PCI_DSS_ST4_TC009_Inadequate_Audit_Logging_Analysis",
        description="Stage 4: analysis quality for missing or weak audit logging controls",
        schema="""
                CREATE TABLE system_access_events (
                    event_id INT PRIMARY KEY,
                    user_id INT,
                    system_component VARCHAR(100),
                    action VARCHAR(50),
                    event_time TIMESTAMP,
                    source_ip VARCHAR(45),
                    success BOOLEAN
                );
                CREATE TABLE audit_log_config (
                    config_id INT PRIMARY KEY,
                    logging_enabled BOOLEAN,
                    retention_days INT,
                    integrity_protection VARCHAR(50),
                    central_time_sync BOOLEAN,
                    review_frequency VARCHAR(50)
                );
            """,
        failed_assertion=(
            "SELECT c.config_id FROM audit_log_config c "
            "WHERE c.logging_enabled = FALSE "
            "OR c.retention_days < 365 "
            "OR c.integrity_protection IS NULL "
            "OR c.central_time_sync = FALSE "
            "OR c.review_frequency IS NULL"
        ),
        failure_result=(
            "config_id: 1, logging_enabled: false, retention_days: 14, "
            "integrity_protection: NULL, central_time_sync: false, review_frequency: NULL"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description=(
                "Inadequate audit logging, monitoring, protection, and retention controls"
            ),
            standard_requirements=[
                "Req 10.2",
                "Req 10.3",
                "Req 10.4",
                "Req 10.5",
                "Req 10.6",
            ],
            required_phrases={
                SynonymSet("audit log", "logging", "log events"),
                SynonymSet(
                    "suspicious activity",
                    "anomaly",
                    "anomalies",
                    "forensic analysis",
                ),
                SynonymSet(
                    "tamper",
                    "unauthorized modification",
                    "integrity",
                    "destruction",
                ),
            },
            preferred_phrases=[
                SynonymSet("monitor", "monitoring", "alerting", "detection"),
                SynonymSet("retention", "log history", "historical logs"),
                SynonymSet("time synchronization", "time sync", "NTP", "clock drift"),
                SynonymSet("system components", "critical security controls", "CDE"),
                SynonymSet(
                    "review logs", "log review", "daily review", "periodic review"
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Enable audit logging on system components",
                    "Implement centralized audit logging",
                ),
                SynonymSet(
                    "Protect logs from unauthorized modification and deletion",
                    "Implement tamper-evident log protection",
                    "Restrict write/delete access to logs",
                ),
                SynonymSet(
                    "Increase log retention to at least one year / 12 months / 365 days",
                    "Retain logs for at least one year / 12 months / 365 days",
                    "Configure long-term log retention",
                ),
                SynonymSet(
                    "Implement centralized time synchronization",
                    "Network Time Protocol (NTP)",
                    "Enable time synchronization across all systems",
                    "Synchronize system clocks",
                ),
                SynonymSet(
                    "Establish and enforce regular audit log review procedures",
                    "Define periodic log review process",
                    "Configure alerts for suspicious activity",
                ),
            ],
        ),
    ),
]
