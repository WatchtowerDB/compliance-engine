from ...benchmark_case import BenchmarkCase
from ...ground_truth import AssertionGenerationGroundTruth
from ...synonym_set import SynonymSet

GDPR_STAGE_2_CASES: list[BenchmarkCase] = [
    # Article 5 — Data minimisation and storage limitation
    BenchmarkCase(
        name="GDPR_ST2_TC001_Article5_Data_Minimisation",
        description="Stage 2: generate assertions for excessive personal data collection and storage",
        schema="""
            CREATE TABLE user_profiles (
                user_id INT PRIMARY KEY,
                email VARCHAR(255),
                phone VARCHAR(30),
                full_name VARCHAR(100),
                home_address TEXT,
                employment_history TEXT,
                salary_information DECIMAL(10, 2),
                medical_history TEXT,
                social_security_number VARCHAR(20),
                passport_number VARCHAR(20),
                created_at TIMESTAMP,
                last_modified_at TIMESTAMP
            );

            CREATE TABLE data_retention_config (
                config_id INT PRIMARY KEY,
                data_category VARCHAR(100),
                retention_days INT,
                auto_purge_enabled BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema collects and stores excessive personal data beyond specified legitimate purposes",
            expected_violation_keywords=[
                SynonymSet("personal data", "personal information", "PII"),
                SynonymSet("minimisation", "minimization", "necessary", "purpose"),
                SynonymSet("retention", "storage", "stored beyond"),
            ],
            expected_tables=["user_profiles", "data_retention_config"],
        ),
    ),
    # Article 9 — Special category data (without safeguards)
    BenchmarkCase(
        name="GDPR_ST2_TC002_Article9_Special_Categories",
        description="Stage 2: generate assertions for unprotected special category data processing",
        schema="""
            CREATE TABLE employee_health_records (
                record_id INT PRIMARY KEY,
                employee_id INT,
                health_condition VARCHAR(255),
                medication_list TEXT,
                medical_provider VARCHAR(100),
                assessment_date TIMESTAMP,
                is_encrypted BOOLEAN,
                consent_obtained BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE religious_affiliations (
                affiliation_id INT PRIMARY KEY,
                employee_id INT,
                religion VARCHAR(100),
                place_of_worship VARCHAR(100),
                attendance_frequency VARCHAR(50)
            );

            CREATE TABLE biometric_data (
                biometric_id INT PRIMARY KEY,
                user_id INT,
                fingerprint BLOB,
                facial_recognition_vector BLOB,
                iris_scan BLOB,
                enrollment_date TIMESTAMP,
                is_anonymized BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema stores special category data (health, religion, biometric) without apparent safeguards",
            expected_violation_keywords=[
                SynonymSet(
                    "special category",
                    "special categories",
                    "special data",
                    "sensitive data",
                ),
                SynonymSet(
                    "health",
                    "medical",
                    "biometric",
                    "genetic",
                    "religious",
                    "political",
                ),
                SynonymSet("consent", "explicit", "legal basis", "safeguard"),
            ],
            expected_tables=[
                "employee_health_records",
                "religious_affiliations",
                "biometric_data",
            ],
        ),
    ),
    # Article 17 — Right to erasure (right to be forgotten)
    BenchmarkCase(
        name="GDPR_ST2_TC003_Article17_Right_Erasure",
        description="Stage 2: generate assertions for missing right-to-erasure implementation",
        schema="""
            CREATE TABLE customers (
                customer_id INT PRIMARY KEY,
                email VARCHAR(255),
                full_name VARCHAR(100),
                phone VARCHAR(30),
                address TEXT,
                account_created_at TIMESTAMP,
                account_status VARCHAR(20),
                last_login_at TIMESTAMP
            );

            CREATE TABLE transaction_history (
                transaction_id INT PRIMARY KEY,
                customer_id INT,
                amount DECIMAL(10, 2),
                transaction_date TIMESTAMP,
                description TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );

            CREATE TABLE customer_archive (
                archive_id INT PRIMARY KEY,
                customer_id INT,
                archived_profile_data TEXT,
                archived_at TIMESTAMP,
                reason VARCHAR(100)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema lacks mechanisms to permanently delete personal data upon user request",
            expected_violation_keywords=[
                SynonymSet(
                    "erasure", "erase", "delete", "forgotten", "right to be forgotten"
                ),
                SynonymSet("personal data", "customer data", "profile"),
                SynonymSet("without delay", "promptly", "timely", "deletion mechanism"),
            ],
            expected_tables=["customers", "transaction_history"],
        ),
    ),
    # Article 25 — Data protection by design and by default
    BenchmarkCase(
        name="GDPR_ST2_TC004_Article25_Protection_By_Design",
        description="Stage 2: generate assertions for missing privacy-by-design controls",
        schema="""
            CREATE TABLE user_data (
                user_id INT PRIMARY KEY,
                username VARCHAR(100),
                password_hash VARCHAR(255),
                email VARCHAR(255),
                personal_notes TEXT,
                location_data POINT,
                browser_history TEXT,
                ip_addresses TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );

            CREATE TABLE data_processing_config (
                config_id INT PRIMARY KEY,
                default_visibility VARCHAR(50),
                default_retention_days INT,
                pseudonymization_enabled BOOLEAN,
                encryption_enabled BOOLEAN
            );

            CREATE TABLE third_party_sharing (
                sharing_id INT PRIMARY KEY,
                user_id INT,
                third_party_name VARCHAR(100),
                data_categories TEXT,
                consent_required BOOLEAN,
                consent_obtained BOOLEAN,
                FOREIGN KEY (user_id) REFERENCES user_data(user_id)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema lacks privacy-by-design principles: no default data minimisation, weak encryption, oversharing",
            expected_violation_keywords=[
                SynonymSet(
                    "privacy by design",
                    "privacy-by-design",
                    "by default",
                    "pseudonymisation",
                    "pseudonymization",
                ),
                SynonymSet("encryption", "encrypted", "secure", "protection"),
                SynonymSet(
                    "data minimisation",
                    "data minimization",
                    "necessity",
                    "purpose limitation",
                ),
            ],
            expected_tables=["user_data", "data_processing_config"],
        ),
    ),
    # Article 32 — Security of processing
    BenchmarkCase(
        name="GDPR_ST2_TC005_Article32_Security_Processing",
        description="Stage 2: generate assertions for inadequate security controls",
        schema="""
            CREATE TABLE personal_data_store (
                record_id INT PRIMARY KEY,
                subject_id INT,
                data_type VARCHAR(100),
                data_value TEXT,
                stored_in_plaintext BOOLEAN,
                access_log_enabled BOOLEAN,
                backup_location VARCHAR(255),
                backup_encrypted BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE system_security_config (
                config_id INT PRIMARY KEY,
                encryption_algorithm VARCHAR(50),
                encryption_enabled BOOLEAN,
                tls_enabled BOOLEAN,
                tls_version VARCHAR(10),
                integrity_checking BOOLEAN,
                resilience_testing_frequency VARCHAR(50),
                incident_response_plan VARCHAR(100)
            );

            CREATE TABLE access_controls (
                access_id INT PRIMARY KEY,
                user_id INT,
                resource_name VARCHAR(100),
                permission_type VARCHAR(50),
                is_restricted BOOLEAN,
                audit_logging BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema stores personal data without appropriate security measures (encryption, access controls, backups)",
            expected_violation_keywords=[
                SynonymSet("security", "secure", "encryption", "cryptography"),
                SynonymSet("confidentiality", "integrity", "availability"),
                SynonymSet(
                    "pseudonymisation",
                    "pseudonymization",
                    "encryption",
                    "access control",
                ),
            ],
            expected_tables=["personal_data_store", "system_security_config"],
        ),
    ),
    # Multi-violation case 1 — Article 5 + Article 9 + Article 25
    BenchmarkCase(
        name="GDPR_ST2_TC006_Multi_MinimisationSpecial_Design",
        description="Stage 2: generate assertions for excessive data, special categories, and missing privacy controls",
        schema="""
            CREATE TABLE member_profiles (
                member_id INT PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(255),
                phone VARCHAR(30),
                home_address TEXT,
                health_conditions TEXT,
                religious_beliefs VARCHAR(100),
                political_affiliations TEXT,
                criminal_history TEXT,
                genetic_information TEXT,
                created_at TIMESTAMP
            );

            CREATE TABLE tracking_data (
                tracking_id INT PRIMARY KEY,
                member_id INT,
                location_history TEXT,
                browsing_history TEXT,
                purchase_history TEXT,
                tracking_enabled_by_default BOOLEAN,
                consent_requested BOOLEAN,
                FOREIGN KEY (member_id) REFERENCES member_profiles(member_id)
            );

            CREATE TABLE data_processors (
                processor_id INT PRIMARY KEY,
                processor_name VARCHAR(100),
                data_shared TEXT,
                purpose VARCHAR(255),
                contract_in_place BOOLEAN
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema combines excessive data collection, special category data, and insufficient privacy controls",
            expected_violation_keywords=[
                SynonymSet(
                    "personal data", "excessive", "minimisation", "minimization"
                ),
                SynonymSet(
                    "health", "religious", "political", "genetic", "special category"
                ),
                SynonymSet(
                    "privacy by design", "privacy-by-design", "consent", "tracking"
                ),
            ],
            expected_tables=["member_profiles", "tracking_data"],
        ),
    ),
    # Multi-violation case 2 — Article 17 + Article 32
    BenchmarkCase(
        name="GDPR_ST2_TC007_Multi_Erasure_Security",
        description="Stage 2: generate assertions for missing erasure capability and weak data security",
        schema="""
            CREATE TABLE user_accounts (
                account_id INT PRIMARY KEY,
                email VARCHAR(255),
                password_hash VARCHAR(255),
                full_name VARCHAR(100),
                personal_notes TEXT,
                account_status VARCHAR(20),
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );

            CREATE TABLE user_activity_logs (
                log_id INT PRIMARY KEY,
                account_id INT,
                action VARCHAR(100),
                timestamp TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT,
                FOREIGN KEY (account_id) REFERENCES user_accounts(account_id)
            );

            CREATE TABLE backup_management (
                backup_id INT PRIMARY KEY,
                backup_location VARCHAR(255),
                data_included TEXT,
                backup_date TIMESTAMP,
                encryption_applied BOOLEAN,
                retention_policy VARCHAR(100)
            );
        """,
        assertion_generation_ground_truth=AssertionGenerationGroundTruth(
            violation_description="Schema lacks erasure capability and has weak security (unencrypted backups, insufficient access control)",
            expected_violation_keywords=[
                SynonymSet("erasure", "erase", "delete", "purge", "forgotten"),
                SynonymSet("encryption", "encrypted", "security", "protected"),
                SynonymSet("backup", "restore", "integrity", "availability"),
            ],
            expected_tables=["user_accounts", "backup_management"],
        ),
    ),
]
