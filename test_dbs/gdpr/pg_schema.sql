-- ============================================================================
-- GDPR Compliance Test Database - NexaCare Ltd.
-- Purpose: ~75% GDPR compliant schema (2 violations, 4 compliant areas)
-- Company: NexaCare Ltd. — a patient appointment & care coordination platform
-- Database: PostgreSQL
-- ============================================================================
--
-- VIOLATION 1: Special category personal data stored without table segregation
--   GDPR: Article 9 (prohibition on processing special categories)
--   GDPR: Article 5(1)(c) (data minimisation — special category mixed with ordinary HR data)
--
-- VIOLATION 2: Session tokens stored in plaintext — no pseudonymisation or encryption
--   GDPR: Article 32(1)(a) (pseudonymisation and encryption of personal data)
--   GDPR: Article 5(1)(f) (integrity and confidentiality)
--
-- COMPLIANT AREAS:
--   - Article 17  : deleted_at columns enable right to erasure across all tables
--   - Article 25  : consent/tracking flags default to FALSE (privacy by default)
--   - Article 5(2): audit_log table supports accountability and record-keeping
--   - Article 5(1)(c) + Article 25: patient_ref UUID pseudonymises data subjects
-- ============================================================================

DROP SCHEMA IF EXISTS nexacare CASCADE;

CREATE SCHEMA nexacare;

-- ============================================================================
-- PATIENTS
-- Stores core identity data for registered patients.
-- COMPLIANT: pseudonymised via patient_ref UUID, deleted_at for right to erasure,
--            consent flags default FALSE (Art. 17, Art. 25, Art. 5(1)(c)).
-- ============================================================================
CREATE TABLE
    nexacare.patients (
        patient_id SERIAL PRIMARY KEY,
        -- Art. 25 / Art. 32: opaque reference used across linked tables instead of exposing PII
        patient_ref UUID NOT NULL DEFAULT gen_random_uuid () UNIQUE,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        date_of_birth DATE NOT NULL,
        phone VARCHAR(20),
        -- Art. 25: privacy-by-default — opt-ins start as FALSE
        marketing_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
        analytics_consent BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- Art. 17: soft-delete column enables right-to-erasure workflow
        deleted_at TIMESTAMP
    );

INSERT INTO
    nexacare.patients (
        first_name,
        last_name,
        email,
        date_of_birth,
        phone,
        marketing_opt_in,
        analytics_consent
    )
VALUES
    (
        'Amelia',
        'Carter',
        'amelia.carter@example.com',
        '1988-03-14',
        '+44 7911 123456',
        FALSE,
        FALSE
    ),
    (
        'Marcus',
        'Okafor',
        'marcus.okafor@example.com',
        '1975-09-22',
        '+44 7700 987654',
        FALSE,
        TRUE
    ),
    (
        'Priya',
        'Nair',
        'priya.nair@example.com',
        '1993-06-05',
        '+44 7833 456789',
        FALSE,
        FALSE
    ),
    (
        'Thomas',
        'Bergmann',
        'thomas.bergmann@example.com',
        '1960-11-30',
        '+44 7922 654321',
        TRUE,
        FALSE
    ),
    (
        'Sofia',
        'Reyes',
        'sofia.reyes@example.com',
        '2001-02-18',
        '+44 7600 111222',
        FALSE,
        FALSE
    );

-- ============================================================================
-- APPOINTMENTS
-- Stores scheduled and historical care appointments.
-- COMPLIANT: references patient_ref (pseudonymised), deleted_at for erasure,
--            reason is limited to a short description (data minimisation).
-- ============================================================================
CREATE TABLE
    nexacare.appointments (
        appointment_id SERIAL PRIMARY KEY,
        -- Pseudonymised reference — no direct PII
        patient_ref UUID NOT NULL REFERENCES nexacare.patients (patient_ref),
        practitioner_id INT NOT NULL,
        appointment_date TIMESTAMP NOT NULL,
        -- Art. 5(1)(c): deliberately constrained to avoid over-collection
        reason VARCHAR(200),
        status VARCHAR(30) NOT NULL DEFAULT 'scheduled',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- Art. 17: right to erasure
        deleted_at TIMESTAMP
    );

INSERT INTO
    nexacare.appointments (
        patient_ref,
        practitioner_id,
        appointment_date,
        reason,
        status
    )
SELECT
    p.patient_ref,
    apt.practitioner_id,
    apt.appointment_date,
    apt.reason,
    apt.status
FROM
    nexacare.patients p
    JOIN (
        VALUES
            (
                'amelia.carter@example.com',
                201,
                TIMESTAMP '2026-05-10 09:00:00',
                'Annual check-up',
                'completed'
            ),
            (
                'marcus.okafor@example.com',
                202,
                TIMESTAMP '2026-05-12 11:30:00',
                'Follow-up consultation',
                'completed'
            ),
            (
                'priya.nair@example.com',
                201,
                TIMESTAMP '2026-06-01 14:00:00',
                'Blood pressure review',
                'scheduled'
            ),
            (
                'thomas.bergmann@example.com',
                203,
                TIMESTAMP '2026-06-15 10:00:00',
                'Cardiology referral',
                'scheduled'
            ),
            (
                'sofia.reyes@example.com',
                202,
                TIMESTAMP '2026-04-20 08:30:00',
                'Vaccination',
                'completed'
            )
    ) AS apt (email, practitioner_id, appointment_date, reason, status) ON p.email = apt.email;

-- ============================================================================
-- CONSENT RECORDS
-- Tracks explicit, purpose-specific consent from data subjects.
-- COMPLIANT: per-purpose granularity, withdrawal timestamps (Art. 5, Art. 7).
-- ============================================================================
CREATE TABLE
    nexacare.consent_records (
        consent_id SERIAL PRIMARY KEY,
        patient_ref UUID NOT NULL REFERENCES nexacare.patients (patient_ref),
        purpose VARCHAR(100) NOT NULL,
        consent_given BOOLEAN NOT NULL,
        consent_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- Art. 17: supports withdrawal and subsequent erasure request workflow
        withdrawn_at TIMESTAMP,
        ip_address VARCHAR(45)
    );

INSERT INTO
    nexacare.consent_records (patient_ref, purpose, consent_given, ip_address)
SELECT
    p.patient_ref,
    cr.purpose,
    cr.consent_given,
    cr.ip_address
FROM
    nexacare.patients p
    JOIN (
        VALUES
            (
                'amelia.carter@example.com',
                'marketing_communications',
                FALSE,
                '10.0.0.14'
            ),
            (
                'amelia.carter@example.com',
                'analytics_processing',
                FALSE,
                '10.0.0.14'
            ),
            (
                'marcus.okafor@example.com',
                'analytics_processing',
                TRUE,
                '10.0.0.22'
            ),
            (
                'marcus.okafor@example.com',
                'marketing_communications',
                FALSE,
                '10.0.0.22'
            ),
            (
                'thomas.bergmann@example.com',
                'marketing_communications',
                TRUE,
                '10.0.1.5'
            )
    ) AS cr (email, purpose, consent_given, ip_address) ON p.email = cr.email;

-- ============================================================================
-- AUDIT LOG
-- Records all significant data-processing events across the platform.
-- COMPLIANT: supports accountability obligation (Art. 5(2)).
-- ============================================================================
CREATE TABLE
    nexacare.audit_log (
        log_id SERIAL PRIMARY KEY,
        event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actor_id VARCHAR(100) NOT NULL,
        event_type VARCHAR(60) NOT NULL,
        table_affected VARCHAR(100),
        -- Uses opaque references — no raw PII in the log itself
        record_ref VARCHAR(100),
        ip_address VARCHAR(45),
        outcome VARCHAR(20) NOT NULL DEFAULT 'success'
    );

INSERT INTO
    nexacare.audit_log (
        event_timestamp,
        actor_id,
        event_type,
        table_affected,
        record_ref,
        ip_address,
        outcome
    )
VALUES
    (
        TIMESTAMP '2026-05-10 09:05:00',
        'practitioner_201',
        'RECORD_READ',
        'appointments',
        'apt-0001',
        '192.168.10.5',
        'success'
    ),
    (
        TIMESTAMP '2026-05-12 11:35:00',
        'practitioner_202',
        'RECORD_READ',
        'appointments',
        'apt-0002',
        '192.168.10.6',
        'success'
    ),
    (
        TIMESTAMP '2026-06-01 13:50:00',
        'scheduler_svc',
        'RECORD_CREATE',
        'appointments',
        'apt-0003',
        '10.0.0.1',
        'success'
    ),
    (
        TIMESTAMP '2026-06-10 08:00:00',
        'admin_ops',
        'RECORD_DELETE',
        'patients',
        'erasure-req-0042',
        '10.0.0.2',
        'success'
    ),
    (
        TIMESTAMP '2026-06-11 17:22:00',
        'unknown',
        'AUTH_FAILURE',
        'session_tokens',
        NULL,
        '185.220.101.9',
        'failure'
    );

-- ============================================================================
-- STAFF
-- Internal HR records for NexaCare employees.
--
-- VIOLATION 1 — Article 9 + Article 5(1)(c):
--   disability_notes and mental_health_status are special category personal
--   data (Art. 9(1)) stored directly in the main HR table alongside ordinary
--   employment data, with no table segregation, no access-control differentiation,
--   and no indication of an Art. 9(2) lawful basis for processing.
-- ============================================================================
CREATE TABLE
    nexacare.staff (
        staff_id SERIAL PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        department VARCHAR(60),
        job_title VARCHAR(100),
        -- VIOLATION 1: special category health data mixed into general HR table
        disability_notes TEXT,
        mental_health_status TEXT,
        salary DECIMAL(12, 2),
        employed_since DATE,
        deleted_at TIMESTAMP
    );

INSERT INTO
    nexacare.staff (
        first_name,
        last_name,
        email,
        department,
        job_title,
        disability_notes,
        mental_health_status,
        salary,
        employed_since
    )
VALUES
    -- VIOLATION 1: special category data recorded for all staff without segregation
    (
        'Lena',
        'Fischer',
        'lena.fischer@nexacare.internal',
        'Clinical Operations',
        'Care Coordinator',
        'Registered hearing impairment — uses hearing aid.',
        'No concerns noted.',
        48000.00,
        '2019-03-01'
    ),
    (
        'James',
        'Osei',
        'james.osei@nexacare.internal',
        'Engineering',
        'Backend Engineer',
        NULL,
        'History of generalised anxiety disorder, managed with medication.',
        95000.00,
        '2021-07-15'
    ),
    (
        'Hannah',
        'Kowalski',
        'hannah.kowalski@nexacare.internal',
        'HR',
        'HR Business Partner',
        'Mobility impairment — remote-first arrangement.',
        'No concerns noted.',
        62000.00,
        '2020-01-10'
    ),
    -- COMPLIANT rows: no special category data captured
    (
        'Raj',
        'Mehta',
        'raj.mehta@nexacare.internal',
        'Engineering',
        'DevOps Lead',
        NULL,
        NULL,
        105000.00,
        '2018-06-01'
    ),
    (
        'Claire',
        'Dubois',
        'claire.dubois@nexacare.internal',
        'Clinical Operations',
        'Head of Clinical Quality',
        NULL,
        NULL,
        88000.00,
        '2017-09-20'
    );

-- ============================================================================
-- SESSION TOKENS
-- Stores active authentication session tokens issued to patients.
--
-- VIOLATION 2 — Article 32(1)(a) + Article 5(1)(f):
--   The token column stores raw bearer tokens in plaintext VARCHAR.
--   Tokens are personal data (they identify a specific data subject's session)
--   and must be pseudonymised or stored as a one-way hash. Plaintext storage
--   means a database dump immediately exposes every active patient session.
-- ============================================================================
CREATE TABLE
    nexacare.session_tokens (
        token_id SERIAL PRIMARY KEY,
        patient_ref UUID NOT NULL REFERENCES nexacare.patients (patient_ref),
        -- VIOLATION 2: raw bearer token — must be hashed (e.g., SHA-256) at rest
        token VARCHAR(512) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        revoked_at TIMESTAMP,
        user_agent TEXT,
        ip_address VARCHAR(45)
    );

INSERT INTO
    nexacare.session_tokens (
        patient_ref,
        token,
        expires_at,
        user_agent,
        ip_address
    )
SELECT
    p.patient_ref,
    st.token,
    st.expires_at,
    st.user_agent,
    st.ip_address
FROM
    nexacare.patients p
    JOIN (
        VALUES
            -- VIOLATION 2: plaintext bearer tokens
            (
                'amelia.carter@example.com',
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbWVsaWEiLCJpYXQiOjE3NDAwMDAwMDB9.plaintext_sig_1',
                TIMESTAMP '2026-07-01 00:00:00',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17)',
                '82.45.12.100'
            ),
            (
                'marcus.okafor@example.com',
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJjdXMiLCJpYXQiOjE3NDAwMDAxMDB9.plaintext_sig_2',
                TIMESTAMP '2026-06-25 00:00:00',
                'Mozilla/5.0 (Android 14)',
                '91.108.4.50'
            ),
            (
                'priya.nair@example.com',
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwcml5YSIsImlhdCI6MTc0MDAwMDIwMH0.plaintext_sig_3',
                TIMESTAMP '2026-07-05 00:00:00',
                'Mozilla/5.0 (Windows NT 10.0)',
                '176.58.22.9'
            ),
            (
                'thomas.bergmann@example.com',
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0aG9tYXMiLCJpYXQiOjE3NDAwMDAzMDB9.plaintext_sig_4',
                TIMESTAMP '2026-06-30 00:00:00',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X)',
                '217.64.33.7'
            ),
            (
                'sofia.reyes@example.com',
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzb2ZpYSIsImlhdCI6MTc0MDAwMDQwMH0.plaintext_sig_5',
                TIMESTAMP '2026-07-10 00:00:00',
                'Mozilla/5.0 (Linux; Android 13)',
                '5.9.200.14'
            )
    ) AS st (email, token, expires_at, user_agent, ip_address) ON p.email = st.email;
