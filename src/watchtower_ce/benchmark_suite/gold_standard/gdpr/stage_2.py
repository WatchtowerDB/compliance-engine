from ...benchmark_case import BenchmarkCase
from ...ground_truth import AssertionGenerationGroundTruth
from ...synonym_set import SynonymSet

GDPR_STAGE_2_CASES: list[BenchmarkCase] = [
    # Article 5(1)(c) — Data minimisation
    BenchmarkCase(
        name="GDPR_ST2_TC001_Article5_Data_Minimisation",
        description="Stage 2: generate assertions for excessive personal data collection",
        schema="""
            CREATE TABLE user_profiles (
                user_id INT PRIMARY KEY,
                email VARCHAR(255),
                full_name VARCHAR(100),
                phone VARCHAR(30),
                home_address TEXT,
                employment_history TEXT,
                salary_information DECIMAL(10, 2),
                medical_history TEXT,
                created_at TIMESTAMP
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema collects and stores excessive personal data beyond specified purposes",
            expected_violation_keywords=[
                SynonymSet(
                    "personal_data",
                    "personal_information",
                    "employment_history",
                    "salary_information",
                    "medical_history",
                ),
                SynonymSet("minimisation", "minimization", "excessive", "unnecessary"),
                SynonymSet("purpose", "necessary", "necessity"),
            ],
            expected_tables=["user_profiles"],
        ),
    ),
    # Article 5(1)(e) — Storage limitation
    BenchmarkCase(
        name="GDPR_ST2_TC002_Article5_Storage_Limitation",
        description="Stage 2: generate assertions for missing data retention limits",
        schema="""
            CREATE TABLE customer_data (
                customer_id INT PRIMARY KEY,
                email VARCHAR(255),
                name VARCHAR(100),
                created_at TIMESTAMP,
                last_accessed TIMESTAMP,
                retention_expiry_date DATE,
                marked_for_deletion BOOLEAN
            );

            CREATE TABLE data_retention_policy (
                policy_id INT PRIMARY KEY,
                data_category VARCHAR(100),
                retention_days INT,
                auto_purge_enabled BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema lacks retention limits; personal data stored indefinitely",
            expected_violation_keywords=[
                SynonymSet(
                    "storage_limitation",
                    "retention",
                    "retention_expiry_date",
                    "auto_purge_enabled",
                ),
                SynonymSet(
                    "retention_days", "expiry", "deletion", "marked_for_deletion"
                ),
                SynonymSet("necessary", "purpose", "necessity"),
            ],
            expected_tables=["customer_data"],
        ),
    ),
    # Article 9 — Special category data
    BenchmarkCase(
        name="GDPR_ST2_TC003_Article9_Special_Categories",
        description="Stage 2: generate assertions for unprotected special category data",
        schema="""
            CREATE TABLE employee_health_records (
                record_id INT PRIMARY KEY,
                employee_id INT,
                health_condition VARCHAR(255),
                medication_list TEXT,
                treatment_type VARCHAR(100),
                is_encrypted BOOLEAN,
                consent_obtained BOOLEAN,
                created_at TIMESTAMP
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema stores special category data (health) without apparent safeguards",
            expected_violation_keywords=[
                SynonymSet(
                    "special_category",
                    "sensitive_data",
                    "health_condition",
                    "medication_list",
                    "medical",
                ),
                SynonymSet("prohibited", "processing", "legal_basis"),
                SynonymSet("consent_obtained", "is_encrypted", "safeguard"),
            ],
            expected_tables=["employee_health_records"],
        ),
    ),
    # Article 10 — Criminal conviction data
    BenchmarkCase(
        name="GDPR_ST2_TC004_Article10_Criminal_Conviction",
        description="Stage 2: generate assertions for improperly processed criminal conviction data",
        schema="""
            CREATE TABLE criminal_records (
                record_id INT PRIMARY KEY,
                subject_id INT,
                conviction_type VARCHAR(100),
                conviction_date DATE,
                authorized_processor BOOLEAN,
                official_authority_oversight BOOLEAN,
                created_at TIMESTAMP
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema processes criminal conviction data without official authority oversight",
            expected_violation_keywords=[
                SynonymSet(
                    "criminal_conviction",
                    "criminal_records",
                    "conviction_type",
                    "conviction_date",
                    "offence",
                ),
                SynonymSet(
                    "official_authority",
                    "official_authority_oversight",
                    "authorized_processor",
                ),
                SynonymSet("legal_basis", "authorization", "authorized"),
            ],
            expected_tables=["criminal_records"],
        ),
    ),
    # Article 17 — Right to erasure
    BenchmarkCase(
        name="GDPR_ST2_TC005_Article17_Right_Erasure",
        description="Stage 2: generate assertions for missing right-to-erasure implementation",
        schema="""
            CREATE TABLE user_accounts (
                account_id INT PRIMARY KEY,
                email VARCHAR(255),
                full_name VARCHAR(100),
                account_created_at TIMESTAMP,
                account_status VARCHAR(20),
                erasure_requested_at TIMESTAMP,
                erasure_completed_at TIMESTAMP
            );

            CREATE TABLE user_transactions (
                transaction_id INT PRIMARY KEY,
                account_id INT,
                amount DECIMAL(10, 2),
                transaction_date TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES user_accounts(account_id)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema lacks mechanisms to permanently delete personal data upon user request",
            expected_violation_keywords=[
                SynonymSet(
                    "erasure",
                    "erase",
                    "delete",
                    "erasure_requested_at",
                    "erasure_completed_at",
                ),
                SynonymSet("without_undue_delay", "promptly", "timely"),
                SynonymSet("personal_data", "user_accounts", "account"),
            ],
            expected_tables=["user_accounts"],
        ),
    ),
    # Article 25 — Data protection by design and by default
    BenchmarkCase(
        name="GDPR_ST2_TC006_Article25_Privacy_By_Design",
        description="Stage 2: generate assertions for missing privacy-by-design controls",
        schema="""
            CREATE TABLE user_tracking (
                tracking_id INT PRIMARY KEY,
                user_id INT,
                tracking_enabled_by_default BOOLEAN,
                cookies_accepted BOOLEAN,
                pseudonymization_applied BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE data_sharing_config (
                config_id INT PRIMARY KEY,
                third_party_name VARCHAR(100),
                default_share BOOLEAN,
                consent_required BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema enables data processing by default without privacy safeguards",
            expected_violation_keywords=[
                SynonymSet(
                    "privacy_by_design", "by_default", "tracking_enabled_by_default"
                ),
                SynonymSet(
                    "pseudonymisation",
                    "pseudonymization",
                    "anonymization",
                    "encryption",
                ),
                SynonymSet("data_minimisation", "minimization", "consent_required"),
            ],
            expected_tables=["user_tracking", "data_sharing_config"],
        ),
    ),
    # Article 32 — Security of processing
    BenchmarkCase(
        name="GDPR_ST2_TC007_Article32_Security_Processing",
        description="Stage 2: generate assertions for inadequate security controls",
        schema="""
            CREATE TABLE personal_data_storage (
                data_id INT PRIMARY KEY,
                subject_id INT,
                data_type VARCHAR(100),
                data_value TEXT,
                encrypted BOOLEAN,
                encryption_algorithm VARCHAR(50),
                backup_created BOOLEAN,
                backup_encrypted BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE system_security_controls (
                control_id INT PRIMARY KEY,
                control_name VARCHAR(100),
                implemented BOOLEAN,
                last_tested_at TIMESTAMP
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema stores personal data without encryption; security controls not implemented",
            expected_violation_keywords=[
                SynonymSet("security_of_processing", "security", "risk", "encrypted"),
                SynonymSet(
                    "encryption",
                    "encrypted",
                    "pseudonymisation",
                    "pseudonymization",
                    "backup_encrypted",
                ),
                SynonymSet("confidentiality", "integrity", "availability"),
            ],
            expected_tables=["personal_data_storage", "system_security_controls"],
        ),
    ),
    # Multi-violation case: Article 5 + Article 25 + Article 32
    BenchmarkCase(
        name="GDPR_ST2_TC008_Multi_Minimisation_Design_Security",
        description="Stage 2: generate assertions for excessive data, missing privacy controls, and weak security",
        schema="""
            CREATE TABLE member_profiles (
                member_id INT PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(255),
                phone VARCHAR(30),
                home_address TEXT,
                employment_history TEXT,
                medical_history TEXT,
                tracking_enabled_by_default BOOLEAN,
                encrypted BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE tracking_log (
                log_id INT PRIMARY KEY,
                member_id INT,
                tracking_event TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES member_profiles(member_id)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema combines excessive data, privacy-by-default failures, and weak encryption",
            expected_violation_keywords=[
                SynonymSet(
                    "minimisation",
                    "minimization",
                    "excessive",
                    "employment_history",
                    "medical_history",
                ),
                SynonymSet(
                    "privacy_by_design", "by_default", "tracking_enabled_by_default"
                ),
                SynonymSet("encrypted", "encryption", "security", "protected"),
            ],
            expected_tables=["member_profiles"],
        ),
    ),
    # Multi-violation case: Article 9 + Article 17
    BenchmarkCase(
        name="GDPR_ST2_TC009_Multi_SpecialData_Erasure",
        description="Stage 2: generate assertions for special category data without erasure capability",
        schema="""
            CREATE TABLE healthcare_provider_records (
                record_id INT PRIMARY KEY,
                patient_id INT,
                health_condition VARCHAR(255),
                diagnosis TEXT,
                treatment_plan TEXT,
                consent_obtained BOOLEAN,
                erasure_capability BOOLEAN,
                created_at TIMESTAMP,
                erasure_requested_at TIMESTAMP
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema stores health data (special category) without erasure mechanism",
            expected_violation_keywords=[
                SynonymSet(
                    "special_category",
                    "health_condition",
                    "medical",
                    "diagnosis",
                    "treatment_plan",
                ),
                SynonymSet("erasure", "erase", "delete", "erasure_capability"),
                SynonymSet("safeguard", "consent_obtained", "legal_basis"),
            ],
            expected_tables=["healthcare_provider_records"],
        ),
    ),
]
