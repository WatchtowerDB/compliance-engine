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
                SynonymSet(
                    "purpose limitation",
                    "specified purpose",
                    "legitimate purpose",
                    "explicit purpose",
                    "incompatible with",
                    "business justification",
                    "lawful basis",
                ),
                SynonymSet(
                    "storage limitation",
                    "permit identification",
                    "permits identification",
                    "retention",
                    "archive",
                    "archiving",
                    "no longer than",
                ),
            },
            preferred_phrases=[
                "Article 89(1)",
                SynonymSet(
                    "disclosure",
                    "data breach",
                    "attack surface",
                    "unauthorized access",
                ),
                SynonymSet(
                    "technical measure",
                    "organisational measure",
                    "controller responsibility",
                    "demonstrate compliance",
                ),
                SynonymSet(
                    "data concerning health",
                    "health data",
                    "medical_history",
                    "medical diagnosis",
                    "management of health",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Audit and remove data not necessary for stated purposes",
                    "Enforce data minimisation at schema level",
                    "Delete unnecessary personal data",
                ),
                SynonymSet(
                    "Define and enforce retention schedules",
                    "Implement automatic data deletion after retention period",
                    "Implement data retention policy / policies",
                ),
                SynonymSet(
                    "Document legitimate purposes for each data category",
                    "Review sensitive data handling purposes and methods",
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
                legal_basis_documented BOOLEAN,
                created_at TIMESTAMP
            );
        """,
        failed_assertion=(
            "SELECT record_id FROM employee_health_records "
            "WHERE health_condition IS NOT NULL "
            "AND (is_encrypted = FALSE OR legal_basis_documented = FALSE)"
        ),
        failure_result=(
            "record_id: 1001, is_encrypted: false, legal_basis_documented: false\n"
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
                    "data concerning health",
                ),
                SynonymSet(
                    "consent",
                    "opt-in",
                ),
                SynonymSet(
                    "prohibited",
                    "legal basis",
                    "legal grounds",
                ),
            },
            preferred_phrases=[
                SynonymSet("Data Protection Impact Assessment", "DPIA"),
                SynonymSet(
                    "purpose limitation",
                    "specified purpose",
                    "legitimate purpose",
                    "explicit purpose",
                    "business justification",
                ),
                SynonymSet(
                    "disclosure",
                    "unauthorized access",
                    "data breach",
                    "attack surface",
                ),
                SynonymSet("confidentiality", "encryption", "data protection"),
            ],
            remediation_steps=[
                SynonymSet(
                    "Consent and basis verification",
                    "Verify consent and basis for processing",
                    "Obtain explicit, informed consent from data subjects",
                    "Implement consent management system",
                    "Document consent mechanism and retention",
                ),
                SynonymSet(
                    "Encrypt special category data",
                    "Implement end-to-end encryption / pseudonymisation for health records",
                    "Secure storage of sensitive data",
                ),
                SynonymSet(
                    "Document legal basis for processing",
                    "Identify applicable exception under Article 9(2)",
                    "Establish Data Processing Agreement with third parties",
                ),
                SynonymSet(
                    "Restrict access to authorised / authorized personnel only",
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
            standard_requirements=["Article 17"],
            required_phrases={
                SynonymSet("erasure", "erase", "delete", "forgotten"),
                SynonymSet("without undue delay", "promptly", "timely basis"),
                SynonymSet(
                    "no longer necessary",
                    "data subject",
                    "purpose limitation",
                    "specified purpose",
                    "legitimate purpose",
                    "explicit purpose",
                    "business justification",
                ),
            },
            preferred_phrases=[
                SynonymSet("Article 6(1)", "Article 9(2)", "Article 9(3)"),
                "Article 21(1)",
                SynonymSet("Union State law", "Member State law"),
                SynonymSet(
                    "storage limitation",
                    "permit identification",
                    "permits identification",
                    "retention",
                    "archive",
                    "archiving",
                    "no longer than",
                ),
                "request",
                SynonymSet("linked", "links", "copies", "replication"),
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
                    "Implement automated enforcement auditing",
                    "Update data retention policy / policies",
                ),
                SynonymSet(
                    "Notify third-party processors and data recipients",
                    "Inform controllers processing linked data",
                    "Document erasure completion",
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
            "tracking_id: 5001, user_id: 1050, tracking_enabled_by_default: true, cookies_accepted: false\n"
            "tracking_id: 5002, user_id: 1051, tracking_enabled_by_default: true, cookies_accepted: false\n"
            "config_id: 12, third_party_name: AdPartner Inc, default_share: true, consent_required: false\n"
            "config_id: 15, third_party_name: AnalyticsVendor Ltd, default_share: true, consent_required: false"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Data processing enabled by default without privacy safeguards; insufficient privacy controls",
            standard_requirements=["Article 25(1)", "Article 25(2)"],
            required_phrases={
                SynonymSet("privacy by design", "privacy-by-design", "by default"),
                SynonymSet(
                    "technical measure",
                    "organisational measure",
                    "organizational measure",
                ),
                SynonymSet(
                    "data minimisation",
                    "data minimization",
                    "pseudonymisation",
                    "pseudonymization",
                ),
            },
            preferred_phrases=[
                SynonymSet(
                    "state of the art", "best practices", "risk assessment", "latest"
                ),
                SynonymSet("processing purpose", "nature and scope", "context"),
                SynonymSet(
                    "breach",
                    "regulatory fine",
                    "reputational damage",
                    "loss of user trust",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Implement privacy-by-design in system architecture",
                    "Integrate privacy considerations from design phase",
                    "Conduct privacy impact assessment",
                    "Apply pseudonymisation to reduce personal data exposure",
                    "Implement data minimisation at the system level",
                    "Limit data visibility to necessary personnel",
                ),
                SynonymSet(
                    "Correct tracking defaults", "Correct data sharing defaults"
                ),
                SynonymSet(
                    "Disable data processing by default unless explicitly consented",
                    "Change default settings to privacy-preserving",
                    "Require opt-in for tracking and data sharing",
                ),
                SynonymSet(
                    "Audit and evaluate security and privacy controls",
                    "Verify security and privacy controls",
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
            "WHERE last_tested_at IS NULL"
        ),
        failure_result=(
            "data_id: 3001, subject_id: 2010, encrypted: false, encryption_algorithm: NULL\n"
            "data_id: 3002, subject_id: 2011, encrypted: false, encryption_algorithm: NULL\n"
            "data_id: 3045, subject_id: 2050, backup_created: true, backup_encrypted: false\n"
            "control_id: 101, control_name: TLS_Version_Check, last_tested_at: NULL\n"
            "control_id: 105, control_name: Access_Log_Review, last_tested_at: NULL"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Personal data stored without encryption; security controls not regularly tested",
            standard_requirements=["Article 32(1)"],
            required_phrases={
                "security of processing",
                SynonymSet(
                    "encryption", "encrypted", "pseudonymisation", "pseudonymization"
                ),
                SynonymSet(
                    "confidentiality", "integrity", "availability", "resilience"
                ),
            },
            preferred_phrases=[
                SynonymSet("incident", "restore availability", "timely manner"),
                SynonymSet(
                    "unauthorised disclosure",
                    "unauthorized disclosure",
                    "unauthorized access",
                    "unauthorised access",
                ),
                SynonymSet("access control", "authentication", "authorization"),
                SynonymSet(
                    "technical measure",
                    "organisational measure",
                    "organizational measure",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Enforce encryption for personal data",
                    "Enctrypt personal data",
                    "Implement AES-256 or equivalent encryption",
                    "Enable encryption by default for all systems",
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
                    "Develop incident response and notification procedures",
                    "Create incident response plan",
                    "Establish notification timelines for breaches",
                ),
            ],
        ),
    ),
    # Article 10 — Processing of criminal convictions and offences
    BenchmarkCase(
        name="GDPR_ST4_TC006_Article10_Criminal_Conviction_Data",
        description="Stage 4: analysis quality for improper handling of criminal conviction data without official authority",
        schema="""
            CREATE TABLE criminal_records (
                record_id INT PRIMARY KEY,
                subject_id INT,
                conviction_type VARCHAR(100),
                offence_description TEXT,
                conviction_date DATE,
                sentence_length INT,
                authorized_processor BOOLEAN,
                official_authority_oversight BOOLEAN,
                legal_basis_documented BOOLEAN,
                access_control_applied BOOLEAN,
                created_at TIMESTAMP
            );

            CREATE TABLE conviction_register (
                register_id INT PRIMARY KEY,
                maintained_by VARCHAR(100),
                is_official_authority BOOLEAN,
                record_count INT,
                last_audited TIMESTAMP
            );
        """,
        failed_assertion=(
            "SELECT record_id FROM criminal_records "
            "WHERE conviction_type IS NOT NULL "
            "AND (authorized_processor = FALSE OR official_authority_oversight = FALSE OR legal_basis_documented = FALSE) "
            "UNION "
            "SELECT register_id FROM conviction_register "
            "WHERE is_official_authority = FALSE"
        ),
        failure_result=(
            "record_id: 5001, subject_id: 3100, conviction_type: Felony, authorized_processor: false, official_authority_oversight: false\n"
            "record_id: 5002, subject_id: 3101, conviction_type: Misdemeanor, legal_basis_documented: false, authorized_processor: false\n"
            "register_id: 201, maintained_by: Private Security Corp, is_official_authority: false, record_count: 12847\n"
            "register_id: 202, maintained_by: HR Analytics Inc, is_official_authority: false, record_count: 5432"
        ),
        assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
            violation_description="Criminal conviction data processed without official authority oversight or documented legal basis; comprehensive register not maintained by official authority",
            standard_requirements=["Article 10"],
            required_phrases={
                SynonymSet(
                    "criminal conviction",
                    "criminal convictions",
                    "offence",
                    "offense",
                    "offences",
                    "offenses",
                ),
                SynonymSet(
                    "official authority",
                    "government authority",
                    "state authority",
                    "public authority",
                ),
                SynonymSet(
                    "legal basis",
                    "authorization",
                    "authorised",
                    "authorized",
                    "Union or Member State law",
                ),
            },
            preferred_phrases=[
                SynonymSet(
                    "safeguards",
                    "appropriate safeguards",
                    "rights and freedoms",
                    "data subject rights",
                ),
                SynonymSet(
                    "security measures",
                    "data protection",
                    "confidentiality",
                    "integrity",
                ),
                SynonymSet(
                    "access control",
                    "role-based access",
                    "restricted access",
                    "need-to-know basis",
                ),
            ],
            remediation_steps=[
                SynonymSet(
                    "Restrict criminal conviction data processing to official authorities only",
                    "Ensure only government / state authorities process criminal conviction data",
                    "Implement strict access controls limiting to official authority personnel",
                    "Transfer criminal conviction register to official authority control",
                    "Remove non-compliant records from the register",
                ),
                SynonymSet(
                    "Document legal basis for processing under Union or Member State law",
                    "Verify compliance with applicable legislation for criminal data",
                    "Establish governance / Data Processing Agreement / DPA with official authority",
                    "Maintain records of legal authorization and safeguards",
                ),
                SynonymSet(
                    "Implement technical and organisational safeguards",
                    "Apply encryption and pseudonymisation to sensitive records",
                    "Establish audit logging and monitoring for criminal records access",
                    "Conduct regular Data Protection Impact Assessment / DPIA",
                ),
                SynonymSet(
                    "Restrict data retention to statutory minimum",
                    "Implement automatic deletion upon sentence completion or rehabilitation",
                    "Define retention schedule aligned with criminal justice requirements",
                    "Remove criminal records after prescribed rehabilitation period",
                ),
            ],
        ),
    ),
]
