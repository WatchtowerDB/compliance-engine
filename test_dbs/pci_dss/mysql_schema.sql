-- ============================================================================
-- PCI DSS Compliance Test Database - Simplified
-- Purpose: Test 3 key PCI DSS violations
-- Database: MySQL
-- ============================================================================
--
-- VIOLATION 1: Unrestricted access to full PAN
--   PCI DSS v4.0: 3.4.2, 7.2.1-7.2.2, 7.3.1-7.3.3, 10.2.1, 10.4.1
--   PCI DSS v3.2.1: 3.3, 7.1, 7.2, 10.2, 10.6
--
-- VIOLATION 2: SAD stored after authorization
--   PCI DSS v4.0: 3.3.1, 3.3.2, 3.2.1
--   PCI DSS v3.2.1: 3.2 (3.2.1, 3.2.2, 3.2.3)
--
-- VIOLATION 3: PAN not properly masked when displayed
--   PCI DSS v4.0: 3.4.1, 3.4.2
--   PCI DSS v3.2.1: 3.3, 3.4
-- ============================================================================
DROP TABLE IF EXISTS audit_logs;

DROP TABLE IF EXISTS transactions;

DROP TABLE IF EXISTS cardholder_data;

DROP TABLE IF EXISTS users;

-- ============================================================================
-- CARDHOLDER DATA
-- ============================================================================
CREATE TABLE
    cardholder_data (
        card_id INT AUTO_INCREMENT PRIMARY KEY,
        customer_id INT NOT NULL,
        cardholder_name VARCHAR(100),
        -- VIOLATION 3: PAN not properly masked
        card_number VARCHAR(50) NOT NULL,
        card_number_masked VARCHAR(50),
        expiry_date VARCHAR(7),
        -- VIOLATION 2: CVV should NEVER be stored (SAD)
        cvv VARCHAR(4),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

INSERT INTO
    cardholder_data (
        customer_id,
        cardholder_name,
        card_number,
        card_number_masked,
        expiry_date,
        cvv
    )
VALUES
    -- VIOLATION 2 & 3: Clear text PAN + CVV stored
    (
        1001,
        'John Smith',
        '4532015112830366',
        '453201******0366',
        '12/2026',
        '123'
    ),
    (
        1002,
        'Jane Doe',
        '5425233430109903',
        '542523******9903',
        '03/2027',
        '456'
    ),
    (
        1003,
        'Bob Wilson',
        '4916338506082832',
        '491633******2832',
        '09/2025',
        '789'
    ),
    -- COMPLIANT: Masked PAN, no CVV
    (
        2001,
        'Alice Johnson',
        '************4589',
        '************4589',
        '06/2027',
        NULL
    ),
    (
        2002,
        'Charlie Brown',
        '************7823',
        '************7823',
        '11/2026',
        NULL
    );

-- ============================================================================
-- TRANSACTIONS
-- ============================================================================
CREATE TABLE
    transactions (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        card_id INT,
        merchant_id INT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        -- VIOLATION 2: Full PAN in transaction logs
        full_pan VARCHAR(20),
        -- VIOLATION 2: SAD data stored after authorization
        sad_data TEXT,
        authorization_code VARCHAR(20),
        response_code VARCHAR(5),
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_by_user VARCHAR(50),
        FOREIGN KEY (card_id) REFERENCES cardholder_data (card_id)
    );

INSERT INTO
    transactions (
        card_id,
        merchant_id,
        amount,
        full_pan,
        sad_data,
        authorization_code,
        response_code,
        processed_by_user
    )
VALUES
    -- VIOLATION 2: Full PAN and SAD stored after authorization
    (
        1,
        101,
        150.00,
        '4532015112830366',
        'CVV=123;PIN_BLOCK=A1B2C3D4',
        'AUTH001',
        '00',
        'user_sales'
    ),
    (
        2,
        101,
        275.50,
        '5425233430109903',
        'CVV=456;TRACK2=5425233430109903D2703',
        'AUTH002',
        '00',
        'user_sales'
    ),
    (
        3,
        102,
        89.99,
        '4916338506082832',
        'CVV=789',
        'AUTH003',
        '00',
        'user_support'
    ),
    -- COMPLIANT: No clear PAN, no SAD
    (
        4,
        101,
        200.00,
        NULL,
        NULL,
        'AUTH004',
        '00',
        'user_sales'
    ),
    (
        5,
        102,
        350.00,
        NULL,
        NULL,
        'AUTH005',
        '00',
        'user_sales'
    );

-- ============================================================================
-- USER ACCESS CONTROL (VIOLATION 1 testing)
-- ============================================================================
CREATE TABLE
    users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100),
        department VARCHAR(50),
        job_title VARCHAR(100),
        -- VIOLATION 1: User should not have unrestricted access to full PAN
        can_view_full_pan TINYINT (1) DEFAULT 0,
        requires_full_pan TINYINT (1) DEFAULT 0,
        access_approved TINYINT (1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

INSERT INTO
    users (
        username,
        email,
        department,
        job_title,
        can_view_full_pan,
        requires_full_pan,
        access_approved
    )
VALUES
    -- VIOLATION 1: Users with full PAN access without business need
    (
        'user_sales',
        'sales@company.com',
        'Sales',
        'Sales Representative',
        1,
        0,
        0
    ),
    (
        'user_support',
        'support@company.com',
        'Support',
        'Customer Support',
        1,
        0,
        0
    ),
    (
        'user_marketing',
        'marketing@company.com',
        'Marketing',
        'Marketing Analyst',
        1,
        0,
        0
    ),
    -- COMPLIANT: Users with proper access control
    (
        'user_fraud',
        'fraud@company.com',
        'Fraud',
        'Fraud Analyst',
        1,
        1,
        1
    ),
    (
        'user_cashier',
        'cashier@company.com',
        'Retail',
        'Cashier',
        0,
        0,
        1
    );

-- ============================================================================
-- AUDIT LOGS
-- ============================================================================
CREATE TABLE
    audit_logs (
        log_id INT AUTO_INCREMENT PRIMARY KEY,
        event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id VARCHAR(50),
        event_type VARCHAR(50),
        event_description TEXT,
        data_accessed VARCHAR(100),
        full_pan_viewed TINYINT (1) DEFAULT 0,
        card_id INT,
        source_ip VARCHAR(45),
        success TINYINT (1) DEFAULT 1
    );

INSERT INTO
    audit_logs (
        event_timestamp,
        user_id,
        event_type,
        event_description,
        data_accessed,
        full_pan_viewed,
        card_id,
        source_ip
    )
VALUES
    -- VIOLATION 1: Unrestricted access to full PAN by users without business need
    (
        '2026-01-15 10:30:00',
        'user_sales',
        'DATA_ACCESS',
        'Viewed full cardholder data',
        'cardholder_data',
        1,
        1,
        '192.168.1.10'
    ),
    (
        '2026-01-15 11:00:00',
        'user_support',
        'DATA_ACCESS',
        'Accessed transaction details with full PAN',
        'transactions',
        1,
        2,
        '192.168.1.11'
    ),
    (
        '2026-01-15 14:20:00',
        'user_marketing',
        'DATA_ACCESS',
        'Exported customer payment data',
        'cardholder_data',
        1,
        3,
        '192.168.1.12'
    ),
    -- COMPLIANT: Authorized access with business justification
    (
        '2026-01-16 09:00:00',
        'user_fraud',
        'DATA_ACCESS',
        'Fraud investigation - Case #12345',
        'cardholder_data',
        1,
        1,
        '192.168.1.50'
    ),
    (
        '2026-01-16 10:00:00',
        'user_cashier',
        'DATA_ACCESS',
        'Processed payment - masked PAN only',
        'cardholder_data',
        0,
        4,
        '192.168.1.20'
    );