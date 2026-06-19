from ...benchmark_case import BenchmarkCase
from ...ground_truth import AssertionGenerationGroundTruth
from ...synonym_set import SynonymSet

PCI_DSS_STAGE_2_CASES: list[BenchmarkCase] = [
    # Requirement 3 — Protect stored account data
    BenchmarkCase(
        name="PCI_DSS_ST2_TC001_Req3_Stored_Account_Data",
        description="Stage 2: generate assertions for prohibited CVV/PAN storage",
        schema="""
            CREATE TABLE customers (
                id INT PRIMARY KEY,
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(30),
                billing_address TEXT,
                created_at TIMESTAMP
            );

            CREATE TABLE payment_methods (
                payment_method_id INT PRIMARY KEY,
                customer_id INT,
                card_number VARCHAR(19),
                cvv VARCHAR(4),
                exp_month INT,
                exp_year INT,
                cardholder_name VARCHAR(100),
                token_reference VARCHAR(255),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            CREATE TABLE invoices (
                invoice_id INT PRIMARY KEY,
                customer_id INT,
                payment_method_id INT,
                amount_cents INT,
                status VARCHAR(20),
                issued_at TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Potential storage of PAN and CVV in plaintext columns",
            expected_violation_keywords=[
                SynonymSet(
                    "cvv",
                    "cvc",
                    "card_verification_value",
                    "SAD",
                    "sensitive_authentication_data",
                ),
                SynonymSet("pan", "card number", "primary_account_number"),
                SynonymSet("plaintext", "unencrypted", "cleartext"),
            ],
            expected_tables=["customers"],
        ),
    ),
    # Requirement 4 — Protect cardholder data during transmission
    BenchmarkCase(
        name="PCI_DSS_ST2_TC002_Req4_Transmission",
        description="Stage 2: generate assertions for insecure transmission endpoints",
        schema="""
            CREATE TABLE api_configs (
                id INT PRIMARY KEY,
                service_name VARCHAR(100),
                endpoint VARCHAR(255),
                protocol VARCHAR(20),
                uses_tls BOOLEAN,
                tls_min_version VARCHAR(10),
                certificate_pinning_enabled BOOLEAN
            );

            CREATE TABLE webhook_subscriptions (
                webhook_id INT PRIMARY KEY,
                subscriber_name VARCHAR(100),
                callback_url VARCHAR(255),
                auth_header_name VARCHAR(100),
                auth_header_value VARCHAR(255),
                created_at TIMESTAMP
            );

            CREATE TABLE network_integrations (
                integration_id INT PRIMARY KEY,
                integration_type VARCHAR(50),
                destination_host VARCHAR(255),
                destination_port INT,
                transport VARCHAR(30),
                notes TEXT
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Endpoints may transmit cardholder data over insecure channels",
            expected_violation_keywords=[
                SynonymSet("transmission", "in_transit", "network"),
                SynonymSet("encrypted", "cryptography"),
            ],
            expected_tables=["api_configs"],
        ),
    ),
    # Requirement 7 — Restrict access by business need-to-know
    BenchmarkCase(
        name="PCI_DSS_ST2_TC003_Req7_Access_Control",
        description="Stage 2: generate assertions for missing least-privilege controls",
        schema="""
            CREATE TABLE users (
                user_id INT PRIMARY KEY,
                username VARCHAR(100),
                department VARCHAR(100),
                is_active BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE roles (
                role_id INT PRIMARY KEY,
                role_name VARCHAR(100),
                description TEXT
            );

            CREATE TABLE user_privileges (
                privilege_id INT PRIMARY KEY,
                user_id INT,
                role_id INT,
                user_name VARCHAR(100),
                table_name VARCHAR(100),
                privilege_type VARCHAR(50),
                granted_by VARCHAR(100),
                granted_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (role_id) REFERENCES roles(role_id)
            );

            CREATE TABLE protected_assets (
                asset_id INT PRIMARY KEY,
                table_name VARCHAR(100),
                data_classification VARCHAR(50),
                owner_team VARCHAR(100)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Privileges may exceed business need-to-know",
            expected_violation_keywords=[
                SynonymSet(
                    "least_privilege",
                    "need_to_know",
                    "need-to-know",
                    "business_need",
                    "business-need",
                    "access_need",
                    "access-need",
                ),
                "privilege_type",
                SynonymSet("role", "permission", "authorization"),
            ],
            expected_tables=["user_privileges"],
        ),
    ),
    # Requirement 8 — Identify and authenticate access
    BenchmarkCase(
        name="PCI_DSS_ST2_TC004_Req8_Authentication",
        description="Stage 2: generate assertions for weak/default credentials and auth controls",
        schema="""
            CREATE TABLE users (
                user_id INT PRIMARY KEY,
                username VARCHAR(100),
                password_hash VARCHAR(255),
                access_level VARCHAR(50),
                password_last_changed_at TIMESTAMP,
                failed_login_attempts INT,
                is_locked BOOLEAN
            );

            CREATE TABLE authentication_methods (
                auth_method_id INT PRIMARY KEY,
                user_id INT,
                method_type VARCHAR(50),
                is_enabled BOOLEAN,
                enrolled_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE login_events (
                login_event_id INT PRIMARY KEY,
                user_id INT,
                source_ip VARCHAR(45),
                user_agent TEXT,
                login_result VARCHAR(20),
                occurred_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Authentication controls may be weak or improperly implemented",
            expected_violation_keywords=[
                SynonymSet("identity", "credential", "auth"),
                SynonymSet("password", "hash", "mfa", "multi-factor", "multi_factor"),
            ],
            expected_tables=["users"],
        ),
    ),
    # Requirement 10 — Logging and monitoring
    BenchmarkCase(
        name="PCI_DSS_ST2_TC005_Req10_Logging_Monitoring",
        description="Stage 2: generate assertions for missing audit logging coverage",
        schema="""
            CREATE TABLE payments (
                payment_id INT PRIMARY KEY,
                pan VARCHAR(19),
                amount DECIMAL(10,2),
                payment_status VARCHAR(20),
                processed_by_user_id INT
            );

            CREATE TABLE audit_log (
                log_id INT PRIMARY KEY,
                event_type VARCHAR(100),
                actor_user_id INT,
                target_table VARCHAR(100),
                target_record_id VARCHAR(100),
                event_timestamp TIMESTAMP,
                event_result VARCHAR(30)
            );

            CREATE TABLE access_events (
                access_event_id INT PRIMARY KEY,
                user_id INT,
                action VARCHAR(100),
                resource_name VARCHAR(100),
                action_timestamp TIMESTAMP,
                source_ip VARCHAR(45)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Audit trail coverage may be insufficient for cardholder data access",
            expected_violation_keywords=[
                SynonymSet("audit", "logging", "log"),
                SynonymSet("timestamp", "created_at", "updated_at"),
            ],
            expected_tables=["payments"],
        ),
    ),
    # Multi-violation case 1 — Req 3 + Req 7 + Req 10
    BenchmarkCase(
        name="PCI_DSS_ST2_TC006_Multi_Stored_Data_Access_Logging",
        description=(
            "Stage 2: generate assertions for combined PAN/CVV storage, broad access, and weak audit trails"
        ),
        schema="""
            CREATE TABLE customer_cards (
                card_id INT PRIMARY KEY,
                customer_id INT,
                pan VARCHAR(19),
                cvv VARCHAR(4),
                cardholder_name VARCHAR(100),
                created_at TIMESTAMP
            );

            CREATE TABLE app_permissions (
                permission_id INT PRIMARY KEY,
                role_name VARCHAR(100),
                table_name VARCHAR(100),
                privilege_type VARCHAR(50),
                granted_at TIMESTAMP
            );

            CREATE TABLE security_log (
                log_id INT PRIMARY KEY,
                event_type VARCHAR(100),
                actor_user_id INT,
                target_table VARCHAR(100)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description=(
                "Schema indicates sensitive card data storage risks, permissive access patterns, and incomplete logging"
            ),
            expected_violation_keywords=[
                SynonymSet("cvv", "cvc", "sensitive_authentication_data", "SAD"),
                SynonymSet("pan", "card_number", "primary_account_number"),
                SynonymSet(
                    "access_control",
                    "least_privilege",
                    "need_to_know",
                    "need-to-know",
                    "business_need",
                    "business-need",
                    "access_need",
                    "access-need",
                    "RBAC",
                    "role-based_access",
                    "role_based_access",
                ),
                SynonymSet("audit", "log", "traceability"),
            ],
            expected_tables=["customer_cards", "app_permissions", "security_log"],
        ),
    ),
    # Multi-violation case 2 — Req 4 + Req 8 + Req 10
    BenchmarkCase(
        name="PCI_DSS_ST2_TC007_Multi_Transmission_Auth_Logging",
        description=(
            "Stage 2: generate assertions for insecure transport, weak authentication controls, and insufficient event logging"
        ),
        schema="""
            CREATE TABLE integrations (
                integration_id INT PRIMARY KEY,
                provider_name VARCHAR(100),
                endpoint_url VARCHAR(255),
                transport_protocol VARCHAR(20),
                tls_version VARCHAR(10)
            );

            CREATE TABLE user_accounts (
                user_id INT PRIMARY KEY,
                username VARCHAR(100),
                password_hash VARCHAR(255),
                mfa_enabled BOOLEAN,
                lockout_enabled BOOLEAN
            );

            CREATE TABLE auth_events (
                event_id INT PRIMARY KEY,
                user_id INT,
                event_type VARCHAR(100),
                event_result VARCHAR(30),
                event_timestamp TIMESTAMP
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description=(
                "Schema suggests transmission security weaknesses, incomplete authentication hardening, and sparse auth monitoring"
            ),
            expected_violation_keywords=[
                SynonymSet(
                    "authentication",
                    "default_credential",
                    "2-factor",
                    "2_factor",
                    "multi-factor",
                    "multi_factor",
                    "MFA",
                    "two-factor",
                    "two_factor",
                    "2FA",
                    "multiple_authentication",
                ),
                SynonymSet("password", "hash", "default", "weak"),
                SynonymSet("audit", "monitoring", "log"),
            ],
            expected_tables=["integrations", "user_accounts", "auth_events"],
        ),
    ),
    # Multi-violation case 3 — Req 3 + Req 4 + Req 7 + Req 8
    BenchmarkCase(
        name="PCI_DSS_ST2_TC008_Multi_Core_Control_Gaps",
        description=(
            "Stage 2: generate assertions for combined card-data storage, transmission, access, and authentication control gaps"
        ),
        schema="""
            CREATE TABLE payment_profiles (
                profile_id INT PRIMARY KEY,
                account_id INT,
                card_number VARCHAR(19),
                security_code VARCHAR(4),
                tokenized BOOLEAN
            );

            CREATE TABLE outbound_endpoints (
                endpoint_id INT PRIMARY KEY,
                service_name VARCHAR(100),
                callback_url VARCHAR(255),
                requires_tls BOOLEAN
            );

            CREATE TABLE role_grants (
                grant_id INT PRIMARY KEY,
                role_name VARCHAR(100),
                object_name VARCHAR(100),
                privilege VARCHAR(50)
            );

            CREATE TABLE admin_credentials (
                credential_id INT PRIMARY KEY,
                username VARCHAR(100),
                password_hash VARCHAR(255),
                mfa_secret VARCHAR(255),
                is_default_credential BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description=(
                "Schema presents overlapping violations across storage, transport, access control, and identity security"
            ),
            expected_violation_keywords=[
                SynonymSet(
                    "cvv", "security_code", "sensitive_authentication_data", "SAD"
                ),
                SynonymSet("pan", "card_number", "unencrypted", "cleartext"),
                SynonymSet("tls", "https", "transmission", "in_transit", "SSL"),
                SynonymSet(
                    "access_control",
                    "least_privilege",
                    "need_to_know",
                    "need-to-know",
                    "business_need",
                    "business-need",
                    "access_need",
                    "access-need",
                    "RBAC",
                    "role-based_access",
                    "role_based_access",
                ),
                SynonymSet(
                    "authentication",
                    "default_credential",
                    "2-factor",
                    "2_factor",
                    "multi-factor",
                    "multi_factor",
                    "MFA",
                    "two-factor",
                    "two_factor",
                    "2FA",
                    "multiple_authentication",
                ),
            ],
            expected_tables=[
                "payment_profiles",
                "outbound_endpoints",
                "role_grants",
                "admin_credentials",
            ],
        ),
    ),
]
