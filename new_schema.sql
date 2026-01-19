-- ============================================================================
-- PCI DSS Compliance Test Database - Simplified
-- Purpose: Test 3 key PCI DSS violations
-- Database: PostgreSQL
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
DROP SCHEMA IF EXISTS operations CASCADE;

CREATE SCHEMA operations;

-- ============================================================================
-- CARDHOLDER DATA
-- ============================================================================
-- Cardholder data storage (VIOLATION 2 & 3 testing)
CREATE TABLE
    operations.cardholder_data (
        card_id SERIAL PRIMARY KEY,
        customer_id INT NOT NULL,
        cardholder_name VARCHAR(100),
        -- VIOLATION 3: PAN not properly masked
        card_number VARCHAR(50) NOT NULL,
        card_number_masked VARCHAR(50), -- Properly masked: 453201******0366
        expiry_date VARCHAR(7),
        -- VIOLATION 2: CVV should NEVER be stored (SAD)
        cvv VARCHAR(4),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- VIOLATION DATA
INSERT INTO
    operations.cardholder_data (
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

-- Transaction logs (VIOLATION 2 testing - SAD storage)
CREATE TABLE
    operations.transactions (
        transaction_id SERIAL PRIMARY KEY,
        card_id INT REFERENCES operations.cardholder_data (card_id),
        merchant_id INT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        -- VIOLATION 2: Full PAN in transaction logs
        full_pan VARCHAR(20),
        -- VIOLATION 2: SAD data (CVV, PIN, Track data) stored after authorization
        sad_data TEXT,
        authorization_code VARCHAR(20),
        response_code VARCHAR(5),
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_by_user VARCHAR(50)
    );

INSERT INTO
    operations.transactions (
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
    operations.users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100),
        department VARCHAR(50),
        job_title VARCHAR(100),
        -- VIOLATION 1: User should not have unrestricted access to full PAN
        can_view_full_pan BOOLEAN DEFAULT FALSE,
        requires_full_pan BOOLEAN DEFAULT FALSE, -- Business need
        access_approved BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

INSERT INTO
    operations.users (
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
        TRUE,
        FALSE,
        FALSE
    ),
    (
        'user_support',
        'support@company.com',
        'Support',
        'Customer Support',
        TRUE,
        FALSE,
        FALSE
    ),
    (
        'user_marketing',
        'marketing@company.com',
        'Marketing',
        'Marketing Analyst',
        TRUE,
        FALSE,
        FALSE
    ),
    -- COMPLIANT: Users with proper access control
    (
        'user_fraud',
        'fraud@company.com',
        'Fraud',
        'Fraud Analyst',
        TRUE,
        TRUE,
        TRUE
    ),
    (
        'user_cashier',
        'cashier@company.com',
        'Retail',
        'Cashier',
        FALSE,
        FALSE,
        TRUE
    );

-- ============================================================================
-- AUDIT LOGS (Track access to cardholder data - VIOLATION 1)
-- ============================================================================
CREATE TABLE
    operations.audit_logs (
        log_id SERIAL PRIMARY KEY,
        event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id VARCHAR(50),
        event_type VARCHAR(50),
        event_description TEXT,
        -- Track what data was accessed
        data_accessed VARCHAR(100),
        full_pan_viewed BOOLEAN DEFAULT FALSE,
        card_id INT,
        source_ip VARCHAR(45),
        success BOOLEAN DEFAULT TRUE
    );

INSERT INTO
    operations.audit_logs (
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
        TRUE,
        1,
        '192.168.1.10'
    ),
    (
        '2026-01-15 11:00:00',
        'user_support',
        'DATA_ACCESS',
        'Accessed transaction details with full PAN',
        'transactions',
        TRUE,
        2,
        '192.168.1.11'
    ),
    (
        '2026-01-15 14:20:00',
        'user_marketing',
        'DATA_ACCESS',
        'Exported customer payment data',
        'cardholder_data',
        TRUE,
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
        TRUE,
        1,
        '192.168.1.50'
    ),
    (
        '2026-01-16 10:00:00',
        'user_cashier',
        'DATA_ACCESS',
        'Processed payment - masked PAN only',
        'cardholder_data',
        FALSE,
        4,
        '192.168.1.20'
    );

-- -- ============================================================================
-- -- COMPLIANCE VIOLATION VIEWS
-- -- ============================================================================
-- -- VIOLATION 1: Unrestricted access to full PAN
-- -- PCI DSS v4.0: 3.4.2, 7.2.1-7.2.2, 7.3.1-7.3.3, 10.2.1, 10.4.1
-- -- PCI DSS v3.2.1: 3.3, 7.1, 7.2, 10.2, 10.6
-- CREATE OR REPLACE VIEW operations.v_violation_1_unrestricted_pan_access AS
-- SELECT 
--     u.user_id,
--     u.username,
--     u.department,
--     u.job_title,
--     u.can_view_full_pan,
--     u.requires_full_pan AS business_need,
--     u.access_approved,
--     COUNT(a.log_id) AS unauthorized_access_count,
--     MAX(a.event_timestamp) AS last_unauthorized_access,
--     CASE 
--         WHEN u.can_view_full_pan = TRUE AND u.requires_full_pan = FALSE THEN 
--             'VIOLATION: User has full PAN access without business need'
--         WHEN u.can_view_full_pan = TRUE AND u.access_approved = FALSE THEN 
--             'VIOLATION: Full PAN access not approved'
--         ELSE 'COMPLIANT'
--     END AS violation_status
-- FROM operations.users u
-- LEFT JOIN operations.audit_logs a 
--     ON a.user_id = u.username 
--     AND a.full_pan_viewed = TRUE
-- WHERE u.can_view_full_pan = TRUE 
--   AND (u.requires_full_pan = FALSE OR u.access_approved = FALSE)
-- GROUP BY u.user_id, u.username, u.department, u.job_title, 
--          u.can_view_full_pan, u.requires_full_pan, u.access_approved;
-- -- VIOLATION 2: SAD (Sensitive Authentication Data) stored after authorization
-- -- PCI DSS v4.0: 3.3.1, 3.3.2, 3.2.1
-- -- PCI DSS v3.2.1: 3.2 (3.2.1, 3.2.2, 3.2.3)
-- CREATE OR REPLACE VIEW operations.v_violation_2_sad_storage AS
-- SELECT 
--     'CVV Stored in Cardholder Data' AS violation_source,
--     card_id AS record_id,
--     customer_id,
--     cardholder_name,
--     'VIOLATION: CVV/CVV2/CVC stored (forbidden SAD)' AS violation_type,
--     created_at AS violation_date
-- FROM operations.cardholder_data
-- WHERE cvv IS NOT NULL
-- UNION ALL
-- SELECT 
--     'SAD in Transaction Logs' AS violation_source,
--     transaction_id AS record_id,
--     card_id AS customer_id,
--     processed_by_user AS cardholder_name,
--     'VIOLATION: Sensitive Authentication Data stored after authorization' AS violation_type,
--     transaction_date AS violation_date
-- FROM operations.transactions
-- WHERE sad_data IS NOT NULL OR full_pan IS NOT NULL;
-- -- VIOLATION 3: PAN not properly masked when displayed
-- -- PCI DSS v4.0: 3.4.1, 3.4.2
-- -- PCI DSS v3.2.1: 3.3, 3.4
-- CREATE OR REPLACE VIEW operations.v_violation_3_unmasked_pan AS
-- SELECT 
--     card_id,
--     customer_id,
--     cardholder_name,
--     card_number,
--     card_number_masked,
--     CASE 
--         WHEN card_number ~ '^[0-9]{13,19}$' THEN 
--             'VIOLATION: Full PAN stored/displayed in clear text'
--         WHEN card_number NOT LIKE '%*%' AND LENGTH(card_number) > 10 THEN
--             'VIOLATION: PAN not properly masked'
--         ELSE 'COMPLIANT: PAN properly masked'
--     END AS violation_status,
--     created_at
-- FROM operations.cardholder_data
-- WHERE card_number ~ '^[0-9]{13,19}$'  -- Full numeric PAN
--    OR (card_number NOT LIKE '%*%' AND LENGTH(card_number) > 10);
-- -- ============================================================================