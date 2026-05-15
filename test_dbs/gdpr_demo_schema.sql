DROP TABLE IF EXISTS gdpr_controls_metadata CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS employee_profiles CASCADE;
DROP TABLE IF EXISTS account_transactions CASCADE;

-- ------------------------------------------------------------------------------
-- 1. METADATA TABLES (GDPRControls)
-- ------------------------------------------------------------------------------

CREATE TABLE gdpr_controls_metadata (
    control_id SERIAL PRIMARY KEY,
    article_reference VARCHAR(50) UNIQUE NOT NULL,
    original_gdpr_text TEXT NOT NULL,
    schema_rule_mapping TEXT NOT NULL,
    severity_level VARCHAR(20) NOT NULL
);

INSERT INTO gdpr_controls_metadata (article_reference, original_gdpr_text, schema_rule_mapping, severity_level) VALUES
('Article 32(1)(a)', 
 'the pseudonymisation and encryption of personal data;', 
 'CHECK: Columns classified as highly sensitive (e.g., SSN, passwords) must not use plaintext VARCHAR/TEXT data types without encryption functions.', 
 'CRITICAL'),

('Article 25(2)', 
 'The controller shall implement appropriate technical and organisational measures for ensuring that, by default, only personal data which are necessary for each specific purpose of the processing are processed.', 
 'CHECK: Boolean columns related to user consent, tracking, or marketing must enforce DEFAULT FALSE.', 
 'HIGH'),

('Article 5(1)(e)', 
 'kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed (storage limitation);', 
 'CHECK: Tables containing Personal Identifiable Information (PII) must include timestamp columns allowing for expiration (e.g., deleted_at, expires_at).', 
 'HIGH'),

('Article 5(1)(c)', 
 'adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed (data minimisation);', 
 'CHECK: Standard user tables must not include Special Category Data (e.g., medical, biometric) without table segregation and strict foreign key constraints.', 
 'MEDIUM'),

('Article 30(1)(g)', 
 'where possible, a general description of the technical and organisational security measures referred to in Article 32(1).', 
 'CHECK: Financial or sensitive transaction tables must include audit columns (e.g., modified_by, updated_at) to track data lifecycle.', 
 'MEDIUM');


-- ------------------------------------------------------------------------------
-- 2. TARGET SCHEMA (WITH INJECTED GDPR VIOLATIONS)
-- ------------------------------------------------------------------------------

-- TARGET TABLE 1: customers
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    
    -- [INJECTED VIOLATION: V-01 | Article 32(1)(a)] (Plaintext sensitive data)
    password VARCHAR(255) NOT NULL,  
    ssn VARCHAR(11) NOT NULL,        
    
    -- [INJECTED VIOLATION: V-02 | Article 25(2)] (Privacy by Default failure)
    marketing_opt_in BOOLEAN DEFAULT TRUE, 
    
    -- [INJECTED VIOLATION: V-03 | Article 5(1)(e)] (Missing retention capability)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TARGET TABLE 2: employee_profiles
CREATE TABLE employee_profiles (
    employee_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    
    -- [INJECTED VIOLATION: V-04 | Article 5(1)(c)] (Data Segregation failure)
    medical_history_notes TEXT, 
    
    salary DECIMAL(15,2)
);

-- TARGET TABLE 3: account_transactions
CREATE TABLE account_transactions (
    tx_id SERIAL PRIMARY KEY,
    account_id INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    
    -- [INJECTED VIOLATION: V-05 | Article 30(1)(g)] (Missing Audit Architecture)
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ------------------------------------------------------------------------------
-- 3. DUMMY DATA FOR TESTING
-- ------------------------------------------------------------------------------

INSERT INTO customers (first_name, last_name, email, password, ssn, marketing_opt_in) VALUES
('John', 'Doe', 'john.doe@example.com', 'password123', '123-45-6789', TRUE),
('Jane', 'Smith', 'jane.smith@example.com', 'qwerty2026', '987-65-4321', TRUE),
('Alice', 'Johnson', 'alice.j@example.com', 'admin!@#', '555-12-3456', FALSE),
('Bob', 'Williams', 'bob.w@example.com', 'ilovecats', '444-99-8888', TRUE),
('Charlie', 'Brown', 'cbrown@example.com', 'snoopy1', '111-22-3333', TRUE);

INSERT INTO employee_profiles (first_name, department, medical_history_notes, salary) VALUES
('Robert', 'HR', 'Type 2 Diabetes, prescribed Metformin. Recent back surgery.', 65000.00),
('Emily', 'Engineering', 'No known allergies. Cleared for work.', 125000.00),
('Michael', 'Sales', 'Severe peanut allergy. Epipen required on site.', 72000.00),
('Sarah', 'Marketing', 'Currently on maternity leave until October.', 85000.00),
('David', 'IT Support', 'History of clinical depression, weekly therapy sessions.', 68000.00);

INSERT INTO account_transactions (account_id, amount, transaction_date) VALUES
(101, 1500.50, '2026-04-01 10:15:00'),
(101, -200.00, '2026-04-02 14:30:00'),
(102, 3450.00, '2026-04-03 09:00:00'),
(103, -15.99,  '2026-04-05 18:45:00'),
(101, -50.00,  '2026-04-06 12:00:00'),
(104, 10000.00, '2026-04-07 16:20:00');
