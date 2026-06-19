from ...benchmark_case import BenchmarkCase
from ...ground_truth import AssertionAnalysisGroundTruth
from ...synonym_set import SynonymSet

GDPR_STAGE_4_CASES: list[BenchmarkCase] = [
    # Article 5 — Data minimisation and storage limitation
    BenchmarkCase(
        name="GDPR_ST4_TC001_Article5_Minimisation",
        description="Stage 4: analysis quality for data minimisation and storage limitation violations",
        schema="""
            CREATE TABLE customer_personal_data (
                customer_id INT PRIMARY KEY,
                email VARCHAR(255),
                phone VARCHAR(30),
                full_name VARCHAR(100),
                date_of_birth DATE,
                home_address TEXT,
                employment_history TEXT,
                salary_information DECIMAL(10, 2),
                medical_history TEXT,
                educational_background TEXT,
                created_at TIMESTAMP,
                data_retention_expiry TIMESTAMP,
                collected_for_purpose VARCHAR(100)
            );
        """,
        failed_assertion=(
            "SELECT customer_id FROM customer_personal_data "
            "WHERE (medical_history IS NOT NULL OR employment_history IS NOT NULL OR salary_information IS NOT NULL) "
            "OR (collected_for_purpose = 'marketing' AND data_retention_expiry IS NULL)"
        ),
        failure_result=(
            "customer_id: 101, medical_history: present, salary_information: present, data_retention_expiry: NULL\n"
            "customer_id: 102, employment_history: present, collected_for_purpose: marketing, data_retention_expiry: NULL"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Personal data collection exceeds specified purposes; storage lacks retention limits",
            standard_requirements=[
                "Article 5(1)(b)",
                "Article 5(1)(c)",
                "Article 5(1)(e)",
            ],
            required_phrases={
                SynonymSet("data minimisation", "data minimization", "necessary"),
                SynonymSet("purpose limitation", "specified purposes", "incompatible"),
                SynonymSet("storage limitation", "retention", "kept no longer"),
            },
            preferred_phrases=[
                SynonymSet("sensitive data", "special category", "excessive"),
                SynonymSet(
                    "lawful basis", "legitimate purpose", "business justification"
                ),
                SynonymSet(
                    "retention policy", "retention schedule", "automatic deletion"
                ),
                SynonymSet(
                    "data controller",
                    "controller responsibility",
                    "demonstrate compliance",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Audit and remove data not necessary for stated purposes",
                    "Delete unnecessary personal data",
                    "Implement data classification to identify excess data",
                ),
                SynonymSet(
                    "Define and enforce retention schedules",
                    "Implement automatic data deletion after retention period",
                    "Establish data retention policy",
                ),
                SynonymSet(
                    "Document legitimate purposes for each data category",
                    "Define business justification for data collection",
                    "Establish purpose limitation controls",
                ),
            ],
        ),
    ),
    # Article 9 — Special category data
    BenchmarkCase(
        name="GDPR_ST4_TC002_Article9_Special_Categories",
        description="Stage 4: analysis quality for unprotected special category data processing",
        schema="""
            CREATE TABLE employee_health_records (
                record_id INT PRIMARY KEY,
                employee_id INT,
                health_condition VARCHAR(255),
                medication_list TEXT,
                treatment_type VARCHAR(100),
                doctor_name VARCHAR(100),
                assessment_date TIMESTAMP,
                is_encrypted BOOLEAN,
                explicit_consent_obtained BOOLEAN,
                legal_basis_documented BOOLEAN,
                created_at TIMESTAMP
            );
        """,
        failed_assertion=(
            "SELECT record_id FROM employee_health_records "
            "WHERE health_condition IS NOT NULL "
            "AND (is_encrypted = FALSE OR explicit_consent_obtained = FALSE OR legal_basis_documented = FALSE)"
        ),
        failure_result=(
            "record_id: 1001, is_encrypted: false, explicit_consent_obtained: false\n"
            "record_id: 1002, legal_basis_documented: false, is_encrypted: false"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Special category data (health) processed without apparent explicit consent or documented legal basis",
            standard_requirements=["Article 9(1)", "Article 9(2)"],
            required_phrases={
                SynonymSet(
                    "special category",
                    "special categories",
                    "sensitive data",
                    "health data",
                ),
                SynonymSet(
                    "explicit consent",
                    "opt-in",
                    "informed consent",
                    "consent mechanism",
                ),
                SynonymSet(
                    "prohibited", "processing shall be prohibited", "legal basis"
                ),
            },
            preferred_phrases=[
                SynonymSet("processing purpose", "legitimate purposes", "safeguards"),
                SynonymSet("data subject", "individual", "employee rights"),
                SynonymSet(
                    "occupational medicine", "health care", "medical professional"
                ),
                SynonymSet("confidentiality", "encryption", "data protection"),
            ],
            remediation_steps=[
                SynonymSet(
                    "Obtain explicit, informed consent from data subjects",
                    "Implement consent management system",
                    "Document consent mechanism and retention",
                ),
                SynonymSet(
                    "Encrypt special category data in transit and at rest",
                    "Implement end-to-end encryption for health records",
                    "Secure storage of sensitive data",
                ),
                SynonymSet(
                    "Document legal basis for processing",
                    "Identify applicable exception under Article 9(2)",
                    "Establish Data Processing Agreement with third parties if needed",
                ),
                SynonymSet(
                    "Restrict access to authorised personnel only",
                    "Implement role-based access control for health data",
                    "Define professional secrecy obligations",
                ),
            ],
        ),
    ),
    # Article 17 — Right to erasure
    BenchmarkCase(
        name="GDPR_ST4_TC003_Article17_Right_Erasure",
        description="Stage 4: analysis quality for right-to-erasure implementation gaps",
        schema="""
            CREATE TABLE user_profiles (
                user_id INT PRIMARY KEY,
                email VARCHAR(255),
                full_name VARCHAR(100),
                phone VARCHAR(30),
                address TEXT,
                account_created_at TIMESTAMP,
                account_status VARCHAR(20),
                erasure_requested_at TIMESTAMP,
                erasure_completed_at TIMESTAMP
            );

            CREATE TABLE user_transactions (
                transaction_id INT PRIMARY KEY,
                user_id INT,
                amount DECIMAL(10, 2),
                transaction_date TIMESTAMP,
                merchant_name VARCHAR(100),
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            );

            CREATE TABLE user_backups (
                backup_id INT PRIMARY KEY,
                user_id INT,
                backup_content TEXT,
                backup_date TIMESTAMP,
                backup_location VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            );
        """,
        failed_assertion=(
            "SELECT u.user_id FROM user_profiles u "
            "WHERE u.erasure_requested_at IS NOT NULL "
            "AND u.erasure_completed_at IS NULL "
            "AND CURRENT_TIMESTAMP - u.erasure_requested_at > INTERVAL '30 days'"
        ),
        failure_result=(
            "user_id: 201, erasure_requested_at: 2024-01-15, erasure_completed_at: NULL (requested 90+ days ago)"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Erasure requests not processed without undue delay; personal data remains accessible",
            standard_requirements=["Article 17(1)", "Article 17(2)", "Article 17(3)"],
            required_phrases={
                SynonymSet(
                    "erasure", "erase", "delete", "forgotten", "right to be forgotten"
                ),
                SynonymSet("without undue delay", "promptly", "timely basis"),
                SynonymSet("right to erasure", "data subject", "obligation"),
            },
            preferred_phrases=[
                SynonymSet(
                    "lawfully processed", "no longer necessary", "purpose limitation"
                ),
                SynonymSet("controller", "processor", "data subject request"),
                SynonymSet("linked data", "copies", "replications"),
                SynonymSet(
                    "technical measures", "implementation", "available technology"
                ),
                SynonymSet("cost", "effort", "reasonable steps"),
            ],
            remediation_steps=[
                SynonymSet(
                    "Establish erasure request process and workflow",
                    "Implement right-to-erasure mechanism",
                    "Create data subject request management system",
                ),
                SynonymSet(
                    "Delete personal data within legally mandated timeframe",
                    "Remove data without undue delay upon verified request",
                    "Cascade deletion across all systems and backups",
                ),
                SynonymSet(
                    "Notify third-party processors and data recipients",
                    "Inform controllers processing linked data",
                    "Document erasure completion",
                ),
                SynonymSet(
                    "Purge backups containing personal data",
                    "Remove from archive and recovery systems",
                    "Verify complete deletion",
                ),
            ],
        ),
    ),
    # Article 25 — Privacy by design and by default
    BenchmarkCase(
        name="GDPR_ST4_TC004_Article25_Privacy_By_Design",
        description="Stage 4: analysis quality for privacy-by-design and privacy-by-default gaps",
        schema="""
            CREATE TABLE user_tracking_system (
                tracking_id INT PRIMARY KEY,
                user_id INT,
                page_visited VARCHAR(255),
                timestamp TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT,
                cookies_accepted BOOLEAN,
                tracking_enabled_by_default BOOLEAN
            );

            CREATE TABLE data_sharing_config (
                config_id INT PRIMARY KEY,
                third_party_name VARCHAR(100),
                data_categories TEXT,
                default_share BOOLEAN,
                consent_required BOOLEAN,
                user_consent_obtained BOOLEAN
            );

            CREATE TABLE default_settings (
                setting_id INT PRIMARY KEY,
                setting_name VARCHAR(100),
                default_value VARCHAR(255),
                user_can_override BOOLEAN,
                privacy_preserving BOOLEAN
            );
        """,
        failed_assertion=(
            "SELECT tracking_id FROM user_tracking_system "
            "WHERE tracking_enabled_by_default = TRUE AND cookies_accepted = FALSE "
            "UNION "
            "SELECT config_id FROM data_sharing_config "
            "WHERE default_share = TRUE AND consent_required = FALSE"
        ),
        failure_result=(
            "Tracking enabled by default: 450 records\n"
            "Data sharing enabled by default without consent: 12 third parties"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Data processing enabled by default without privacy safeguards; insufficient privacy controls",
            standard_requirements=["Article 25(1)", "Article 25(2)"],
            required_phrases={
                SynonymSet("privacy by design", "privacy-by-design", "by default"),
                SynonymSet(
                    "appropriate technical",
                    "organisational measures",
                    "organizational measures",
                ),
                SynonymSet(
                    "data minimisation",
                    "data minimization",
                    "pseudonymisation",
                    "pseudonymization",
                ),
            },
            preferred_phrases=[
                SynonymSet("state of the art", "best practices", "risk assessment"),
                SynonymSet("processing purpose", "nature and scope", "context"),
                SynonymSet("safeguards", "protect rights", "data subject"),
                SynonymSet("processing systems", "services", "resilience"),
            ],
            remediation_steps=[
                SynonymSet(
                    "Implement privacy-by-design in system architecture",
                    "Integrate privacy considerations from design phase",
                    "Conduct privacy impact assessment",
                ),
                SynonymSet(
                    "Disable data processing by default unless explicitly consented",
                    "Change default settings to privacy-preserving",
                    "Require opt-in for tracking and data sharing",
                ),
                SynonymSet(
                    "Apply pseudonymisation to reduce personal data exposure",
                    "Implement data minimisation at the system level",
                    "Limit data visibility to necessary personnel",
                ),
                SynonymSet(
                    "Test and evaluate security and privacy controls regularly",
                    "Perform penetration testing and privacy audits",
                    "Document compliance measures",
                ),
            ],
        ),
    ),
    # Article 32 — Security of processing
    BenchmarkCase(
        name="GDPR_ST4_TC005_Article32_Security_Processing",
        description="Stage 4: analysis quality for inadequate security of personal data processing",
        schema="""
            CREATE TABLE personal_data_storage (
                data_id INT PRIMARY KEY,
                subject_id INT,
                data_category VARCHAR(100),
                data_value TEXT,
                encrypted BOOLEAN,
                encryption_algorithm VARCHAR(50),
                access_control_applied BOOLEAN,
                backup_created BOOLEAN,
                backup_encrypted BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE system_security_controls (
                control_id INT PRIMARY KEY,
                control_name VARCHAR(100),
                implemented BOOLEAN,
                last_tested_at TIMESTAMP,
                test_frequency VARCHAR(50)
            );

            CREATE TABLE security_incident_log (
                incident_id INT PRIMARY KEY,
                incident_type VARCHAR(100),
                affected_data_records INT,
                detected_at TIMESTAMP,
                response_initiated_at TIMESTAMP,
                resolved_at TIMESTAMP
            );
        """,
        failed_assertion=(
            "SELECT data_id FROM personal_data_storage "
            "WHERE encrypted = FALSE "
            "OR (backup_created = TRUE AND backup_encrypted = FALSE) "
            "UNION "
            "SELECT control_id FROM system_security_controls "
            "WHERE implemented = FALSE OR last_tested_at IS NULL"
        ),
        failure_result=(
            "Unencrypted personal data: 2845 records\n"
            "Unencrypted backups: 15 backup sets\n"
            "Security controls not tested: 8 controls"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Personal data stored without encryption; security controls not regularly tested",
            standard_requirements=[
                "Article 32(1)",
                "Article 32(1)(a)",
                "Article 32(1)(d)",
            ],
            required_phrases={
                SynonymSet("security of processing", "appropriate security", "risk"),
                SynonymSet(
                    "encryption", "encrypted", "pseudonymisation", "pseudonymization"
                ),
                SynonymSet("confidentiality", "integrity", "availability"),
            },
            preferred_phrases=[
                SynonymSet("resilience", "restore availability", "timely manner"),
                SynonymSet("incident response", "detection", "response measures"),
                SynonymSet("access control", "authentication", "authorization"),
                SynonymSet("monitoring", "audit logs", "security testing"),
            ],
            remediation_steps=[
                SynonymSet(
                    "Encrypt all personal data in transit and at rest",
                    "Implement AES-256 or equivalent encryption",
                    "Enable encryption by default for all systems",
                ),
                SynonymSet(
                    "Implement strict access controls and role-based permissions",
                    "Enforce least privilege principle",
                    "Use multi-factor authentication",
                ),
                SynonymSet(
                    "Encrypt backups and test recovery procedures",
                    "Store backups in secure, encrypted locations",
                    "Verify backup integrity regularly",
                ),
                SynonymSet(
                    "Establish regular security testing and assessments",
                    "Conduct penetration testing and vulnerability scans",
                    "Implement continuous security monitoring",
                ),
                SynonymSet(
                    "Develop incident response and notification procedures",
                    "Create incident response plan",
                    "Establish notification timelines for breaches",
                ),
            ],
        ),
    ),
]
