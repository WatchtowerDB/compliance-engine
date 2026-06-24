--
-- PostgreSQL database dump
--

\restrict NrQbWYaV35a0Hmkwjv3bLtf5jUeW3m1cz75nvhoJqUq7jcaV58vSATIKPhb3o9a

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: nexacare; Type: SCHEMA; Schema: -; Owner: testuser
--

CREATE SCHEMA nexacare;


ALTER SCHEMA nexacare OWNER TO testuser;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: appointments; Type: TABLE; Schema: nexacare; Owner: testuser
--

CREATE TABLE nexacare.appointments (
    appointment_id integer NOT NULL,
    patient_ref uuid NOT NULL,
    practitioner_id integer NOT NULL,
    appointment_date timestamp without time zone NOT NULL,
    reason character varying(200),
    status character varying(30) DEFAULT 'scheduled'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE nexacare.appointments OWNER TO testuser;

--
-- Name: appointments_appointment_id_seq; Type: SEQUENCE; Schema: nexacare; Owner: testuser
--

CREATE SEQUENCE nexacare.appointments_appointment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE nexacare.appointments_appointment_id_seq OWNER TO testuser;

--
-- Name: appointments_appointment_id_seq; Type: SEQUENCE OWNED BY; Schema: nexacare; Owner: testuser
--

ALTER SEQUENCE nexacare.appointments_appointment_id_seq OWNED BY nexacare.appointments.appointment_id;


--
-- Name: audit_log; Type: TABLE; Schema: nexacare; Owner: testuser
--

CREATE TABLE nexacare.audit_log (
    log_id integer NOT NULL,
    event_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    actor_id character varying(100) NOT NULL,
    event_type character varying(60) NOT NULL,
    table_affected character varying(100),
    record_ref character varying(100),
    ip_address character varying(45),
    outcome character varying(20) DEFAULT 'success'::character varying NOT NULL
);


ALTER TABLE nexacare.audit_log OWNER TO testuser;

--
-- Name: audit_log_log_id_seq; Type: SEQUENCE; Schema: nexacare; Owner: testuser
--

CREATE SEQUENCE nexacare.audit_log_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE nexacare.audit_log_log_id_seq OWNER TO testuser;

--
-- Name: audit_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: nexacare; Owner: testuser
--

ALTER SEQUENCE nexacare.audit_log_log_id_seq OWNED BY nexacare.audit_log.log_id;


--
-- Name: consent_records; Type: TABLE; Schema: nexacare; Owner: testuser
--

CREATE TABLE nexacare.consent_records (
    consent_id integer NOT NULL,
    patient_ref uuid NOT NULL,
    purpose character varying(100) NOT NULL,
    consent_given boolean NOT NULL,
    consent_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    withdrawn_at timestamp without time zone,
    ip_address character varying(45)
);


ALTER TABLE nexacare.consent_records OWNER TO testuser;

--
-- Name: consent_records_consent_id_seq; Type: SEQUENCE; Schema: nexacare; Owner: testuser
--

CREATE SEQUENCE nexacare.consent_records_consent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE nexacare.consent_records_consent_id_seq OWNER TO testuser;

--
-- Name: consent_records_consent_id_seq; Type: SEQUENCE OWNED BY; Schema: nexacare; Owner: testuser
--

ALTER SEQUENCE nexacare.consent_records_consent_id_seq OWNED BY nexacare.consent_records.consent_id;


--
-- Name: patients; Type: TABLE; Schema: nexacare; Owner: testuser
--

CREATE TABLE nexacare.patients (
    patient_id integer NOT NULL,
    patient_ref uuid DEFAULT gen_random_uuid() NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    date_of_birth date NOT NULL,
    phone character varying(20),
    marketing_opt_in boolean DEFAULT false NOT NULL,
    analytics_consent boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE nexacare.patients OWNER TO testuser;

--
-- Name: patients_patient_id_seq; Type: SEQUENCE; Schema: nexacare; Owner: testuser
--

CREATE SEQUENCE nexacare.patients_patient_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE nexacare.patients_patient_id_seq OWNER TO testuser;

--
-- Name: patients_patient_id_seq; Type: SEQUENCE OWNED BY; Schema: nexacare; Owner: testuser
--

ALTER SEQUENCE nexacare.patients_patient_id_seq OWNED BY nexacare.patients.patient_id;


--
-- Name: session_tokens; Type: TABLE; Schema: nexacare; Owner: testuser
--

CREATE TABLE nexacare.session_tokens (
    token_id integer NOT NULL,
    patient_ref uuid NOT NULL,
    token character varying(512) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    revoked_at timestamp without time zone,
    user_agent text,
    ip_address character varying(45)
);


ALTER TABLE nexacare.session_tokens OWNER TO testuser;

--
-- Name: session_tokens_token_id_seq; Type: SEQUENCE; Schema: nexacare; Owner: testuser
--

CREATE SEQUENCE nexacare.session_tokens_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE nexacare.session_tokens_token_id_seq OWNER TO testuser;

--
-- Name: session_tokens_token_id_seq; Type: SEQUENCE OWNED BY; Schema: nexacare; Owner: testuser
--

ALTER SEQUENCE nexacare.session_tokens_token_id_seq OWNED BY nexacare.session_tokens.token_id;


--
-- Name: staff; Type: TABLE; Schema: nexacare; Owner: testuser
--

CREATE TABLE nexacare.staff (
    staff_id integer NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    department character varying(60),
    job_title character varying(100),
    disability_notes text,
    mental_health_status text,
    salary numeric(12,2),
    employed_since date,
    deleted_at timestamp without time zone
);


ALTER TABLE nexacare.staff OWNER TO testuser;

--
-- Name: staff_staff_id_seq; Type: SEQUENCE; Schema: nexacare; Owner: testuser
--

CREATE SEQUENCE nexacare.staff_staff_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE nexacare.staff_staff_id_seq OWNER TO testuser;

--
-- Name: staff_staff_id_seq; Type: SEQUENCE OWNED BY; Schema: nexacare; Owner: testuser
--

ALTER SEQUENCE nexacare.staff_staff_id_seq OWNED BY nexacare.staff.staff_id;


--
-- Name: appointments appointment_id; Type: DEFAULT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.appointments ALTER COLUMN appointment_id SET DEFAULT nextval('nexacare.appointments_appointment_id_seq'::regclass);


--
-- Name: audit_log log_id; Type: DEFAULT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.audit_log ALTER COLUMN log_id SET DEFAULT nextval('nexacare.audit_log_log_id_seq'::regclass);


--
-- Name: consent_records consent_id; Type: DEFAULT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.consent_records ALTER COLUMN consent_id SET DEFAULT nextval('nexacare.consent_records_consent_id_seq'::regclass);


--
-- Name: patients patient_id; Type: DEFAULT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.patients ALTER COLUMN patient_id SET DEFAULT nextval('nexacare.patients_patient_id_seq'::regclass);


--
-- Name: session_tokens token_id; Type: DEFAULT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.session_tokens ALTER COLUMN token_id SET DEFAULT nextval('nexacare.session_tokens_token_id_seq'::regclass);


--
-- Name: staff staff_id; Type: DEFAULT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.staff ALTER COLUMN staff_id SET DEFAULT nextval('nexacare.staff_staff_id_seq'::regclass);


--
-- Name: appointments appointments_pkey; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.appointments
    ADD CONSTRAINT appointments_pkey PRIMARY KEY (appointment_id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (log_id);


--
-- Name: consent_records consent_records_pkey; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.consent_records
    ADD CONSTRAINT consent_records_pkey PRIMARY KEY (consent_id);


--
-- Name: patients patients_email_key; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.patients
    ADD CONSTRAINT patients_email_key UNIQUE (email);


--
-- Name: patients patients_patient_ref_key; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.patients
    ADD CONSTRAINT patients_patient_ref_key UNIQUE (patient_ref);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (patient_id);


--
-- Name: session_tokens session_tokens_pkey; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.session_tokens
    ADD CONSTRAINT session_tokens_pkey PRIMARY KEY (token_id);


--
-- Name: staff staff_email_key; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.staff
    ADD CONSTRAINT staff_email_key UNIQUE (email);


--
-- Name: staff staff_pkey; Type: CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.staff
    ADD CONSTRAINT staff_pkey PRIMARY KEY (staff_id);


--
-- Name: appointments appointments_patient_ref_fkey; Type: FK CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.appointments
    ADD CONSTRAINT appointments_patient_ref_fkey FOREIGN KEY (patient_ref) REFERENCES nexacare.patients(patient_ref);


--
-- Name: consent_records consent_records_patient_ref_fkey; Type: FK CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.consent_records
    ADD CONSTRAINT consent_records_patient_ref_fkey FOREIGN KEY (patient_ref) REFERENCES nexacare.patients(patient_ref);


--
-- Name: session_tokens session_tokens_patient_ref_fkey; Type: FK CONSTRAINT; Schema: nexacare; Owner: testuser
--

ALTER TABLE ONLY nexacare.session_tokens
    ADD CONSTRAINT session_tokens_patient_ref_fkey FOREIGN KEY (patient_ref) REFERENCES nexacare.patients(patient_ref);


--
-- PostgreSQL database dump complete
--

\unrestrict NrQbWYaV35a0Hmkwjv3bLtf5jUeW3m1cz75nvhoJqUq7jcaV58vSATIKPhb3o9a

