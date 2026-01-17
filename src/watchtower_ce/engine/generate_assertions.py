#!/usr/bin/env python3

import os
from pathlib import Path

from .models.download_model import download_model
from .scripts.pci_compliance_checker import PCIComplianceChecker

SCRIPT_DIR = Path(__file__).parent
MODEL_PATH: Path = Path(
    os.getenv(
        "WTCE_MODEL_PATH",
        SCRIPT_DIR.parent.parent.parent
        / "models/base/Ministral-8B-Instruct-2410-GGUF/Ministral-8B-Instruct-2410-Q6_K_L.gguf",
    )
)
CHROMA_DIR: Path = Path(
    os.getenv("WTCE_CHROMA_DIR", SCRIPT_DIR.parent.parent.parent / "data/chroma_db")
)

if not MODEL_PATH.exists():
    # There already are guardrails within this function but container logic is a little hard to predict.
    download_model(
        "bartowski/Ministral-8B-Instruct-2410-GGUF",
        "Ministral-8B-Instruct-2410-GGUF",
        ["Ministral-8B-Instruct-2410-Q6_K_L.gguf"],
    )


# Example schema with multiple PCI-DSS violations
"""
    The violations:
    credit_card_number VARCHAR(16),  -- Violation: Unencrypted PAN
    cvv VARCHAR(4),                  -- Violation: Storing CVV (prohibited)

    card_number VARCHAR(16),         -- Violation: Unencrypted PAN

    pan VARCHAR(19),                 -- Violation: Unencrypted PAN
    security_code VARCHAR(4)         -- Violation: Storing CVV

    If the model works, it should generate at least 5 assertions. InshaAllah.
"""
SQL_SCHEMA = r"""
--
-- PostgreSQL database dump
--

\restrict itFdgHMTAgzqa6reR7crJ5g4NwluOVNblRJ7USYjsWLZWwgbQ7Xr6n7aYkbEHSn

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: operations; Type: SCHEMA; Schema: -; Owner: myuser
--

CREATE SCHEMA operations;


ALTER SCHEMA operations OWNER TO myuser;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_logs; Type: TABLE; Schema: operations; Owner: myuser
--

CREATE TABLE operations.audit_logs (
    log_id integer NOT NULL,
    event_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id character varying(50),
    event_type character varying(50),
    event_description text,
    data_accessed character varying(100),
    full_pan_viewed boolean DEFAULT false,
    card_id integer,
    source_ip character varying(45),
    success boolean DEFAULT true
);


ALTER TABLE operations.audit_logs OWNER TO myuser;

--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE; Schema: operations; Owner: myuser
--

CREATE SEQUENCE operations.audit_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE operations.audit_logs_log_id_seq OWNER TO myuser;

--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: operations; Owner: myuser
--

ALTER SEQUENCE operations.audit_logs_log_id_seq OWNED BY operations.audit_logs.log_id;


--
-- Name: cardholder_data; Type: TABLE; Schema: operations; Owner: myuser
--

CREATE TABLE operations.cardholder_data (
    card_id integer NOT NULL,
    customer_id integer NOT NULL,
    cardholder_name character varying(100),
    card_number character varying(50) NOT NULL,
    card_number_masked character varying(50),
    expiry_date character varying(7),
    cvv character varying(4),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE operations.cardholder_data OWNER TO myuser;

--
-- Name: cardholder_data_card_id_seq; Type: SEQUENCE; Schema: operations; Owner: myuser
--

CREATE SEQUENCE operations.cardholder_data_card_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE operations.cardholder_data_card_id_seq OWNER TO myuser;

--
-- Name: cardholder_data_card_id_seq; Type: SEQUENCE OWNED BY; Schema: operations; Owner: myuser
--

ALTER SEQUENCE operations.cardholder_data_card_id_seq OWNED BY operations.cardholder_data.card_id;


--
-- Name: transactions; Type: TABLE; Schema: operations; Owner: myuser
--

CREATE TABLE operations.transactions (
    transaction_id integer NOT NULL,
    card_id integer,
    merchant_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    full_pan character varying(20),
    sad_data text,
    authorization_code character varying(20),
    response_code character varying(5),
    transaction_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    processed_by_user character varying(50)
);


ALTER TABLE operations.transactions OWNER TO myuser;

--
-- Name: transactions_transaction_id_seq; Type: SEQUENCE; Schema: operations; Owner: myuser
--

CREATE SEQUENCE operations.transactions_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE operations.transactions_transaction_id_seq OWNER TO myuser;

--
-- Name: transactions_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: operations; Owner: myuser
--

ALTER SEQUENCE operations.transactions_transaction_id_seq OWNED BY operations.transactions.transaction_id;


--
-- Name: users; Type: TABLE; Schema: operations; Owner: myuser
--

CREATE TABLE operations.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100),
    department character varying(50),
    job_title character varying(100),
    can_view_full_pan boolean DEFAULT false,
    requires_full_pan boolean DEFAULT false,
    access_approved boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE operations.users OWNER TO myuser;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: operations; Owner: myuser
--

CREATE SEQUENCE operations.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE operations.users_user_id_seq OWNER TO myuser;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: operations; Owner: myuser
--

ALTER SEQUENCE operations.users_user_id_seq OWNED BY operations.users.user_id;


--
-- Name: v_violation_1_unrestricted_pan_access; Type: VIEW; Schema: operations; Owner: myuser
--

CREATE VIEW operations.v_violation_1_unrestricted_pan_access AS
 SELECT u.user_id,
    u.username,
    u.department,
    u.job_title,
    u.can_view_full_pan,
    u.requires_full_pan AS business_need,
    u.access_approved,
    count(a.log_id) AS unauthorized_access_count,
    max(a.event_timestamp) AS last_unauthorized_access,
        CASE
            WHEN ((u.can_view_full_pan = true) AND (u.requires_full_pan = false)) THEN 'VIOLATION: User has full PAN access without business need'::text
            WHEN ((u.can_view_full_pan = true) AND (u.access_approved = false)) THEN 'VIOLATION: Full PAN access not approved'::text
            ELSE 'COMPLIANT'::text
        END AS violation_status
   FROM (operations.users u
     LEFT JOIN operations.audit_logs a ON ((((a.user_id)::text = (u.username)::text) AND (a.full_pan_viewed = true))))
  WHERE ((u.can_view_full_pan = true) AND ((u.requires_full_pan = false) OR (u.access_approved = false)))
  GROUP BY u.user_id, u.username, u.department, u.job_title, u.can_view_full_pan, u.requires_full_pan, u.access_approved;


ALTER TABLE operations.v_violation_1_unrestricted_pan_access OWNER TO myuser;

--
-- Name: v_violation_2_sad_storage; Type: VIEW; Schema: operations; Owner: myuser
--

CREATE VIEW operations.v_violation_2_sad_storage AS
 SELECT 'CVV Stored in Cardholder Data'::text AS violation_source,
    cardholder_data.card_id AS record_id,
    cardholder_data.customer_id,
    cardholder_data.cardholder_name,
    'VIOLATION: CVV/CVV2/CVC stored (forbidden SAD)'::text AS violation_type,
    cardholder_data.created_at AS violation_date
   FROM operations.cardholder_data
  WHERE (cardholder_data.cvv IS NOT NULL)
UNION ALL
 SELECT 'SAD in Transaction Logs'::text AS violation_source,
    transactions.transaction_id AS record_id,
    transactions.card_id AS customer_id,
    transactions.processed_by_user AS cardholder_name,
    'VIOLATION: Sensitive Authentication Data stored after authorization'::text AS violation_type,
    transactions.transaction_date AS violation_date
   FROM operations.transactions
  WHERE ((transactions.sad_data IS NOT NULL) OR (transactions.full_pan IS NOT NULL));


ALTER TABLE operations.v_violation_2_sad_storage OWNER TO myuser;

--
-- Name: v_violation_3_unmasked_pan; Type: VIEW; Schema: operations; Owner: myuser
--

CREATE VIEW operations.v_violation_3_unmasked_pan AS
 SELECT cardholder_data.card_id,
    cardholder_data.customer_id,
    cardholder_data.cardholder_name,
    cardholder_data.card_number,
    cardholder_data.card_number_masked,
        CASE
            WHEN ((cardholder_data.card_number)::text ~ '^[0-9]{13,19}$'::text) THEN 'VIOLATION: Full PAN stored/displayed in clear text'::text
            WHEN (((cardholder_data.card_number)::text !~~ '%*%'::text) AND (length((cardholder_data.card_number)::text) > 10)) THEN 'VIOLATION: PAN not properly masked'::text
            ELSE 'COMPLIANT: PAN properly masked'::text
        END AS violation_status,
    cardholder_data.created_at
   FROM operations.cardholder_data
  WHERE (((cardholder_data.card_number)::text ~ '^[0-9]{13,19}$'::text) OR (((cardholder_data.card_number)::text !~~ '%*%'::text) AND (length((cardholder_data.card_number)::text) > 10)));


ALTER TABLE operations.v_violation_3_unmasked_pan OWNER TO myuser;

--
-- Name: audit_logs log_id; Type: DEFAULT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.audit_logs ALTER COLUMN log_id SET DEFAULT nextval('operations.audit_logs_log_id_seq'::regclass);


--
-- Name: cardholder_data card_id; Type: DEFAULT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.cardholder_data ALTER COLUMN card_id SET DEFAULT nextval('operations.cardholder_data_card_id_seq'::regclass);


--
-- Name: transactions transaction_id; Type: DEFAULT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.transactions ALTER COLUMN transaction_id SET DEFAULT nextval('operations.transactions_transaction_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.users ALTER COLUMN user_id SET DEFAULT nextval('operations.users_user_id_seq'::regclass);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (log_id);


--
-- Name: cardholder_data cardholder_data_pkey; Type: CONSTRAINT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.cardholder_data
    ADD CONSTRAINT cardholder_data_pkey PRIMARY KEY (card_id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (transaction_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: transactions transactions_card_id_fkey; Type: FK CONSTRAINT; Schema: operations; Owner: myuser
--

ALTER TABLE ONLY operations.transactions
    ADD CONSTRAINT transactions_card_id_fkey FOREIGN KEY (card_id) REFERENCES operations.cardholder_data(card_id);


--
-- PostgreSQL database dump complete
--

\unrestrict itFdgHMTAgzqa6reR7crJ5g4NwluOVNblRJ7USYjsWLZWwgbQ7Xr6n7aYkbEHSn
"""

# Initialize the PCI compliance checker
checker = PCIComplianceChecker(
    model_path=MODEL_PATH, chroma_dir=CHROMA_DIR, collection_name="PCI-DSS-v4.0.1"
)

print("=" * 80)
print("STEP 1: GENERATING SQL ASSERTIONS")
print("=" * 80)

# Generate SQL assertions
assertions = checker.generate_assertions(SQL_SCHEMA)

print("\n" + "=" * 80)
print("GENERATED ASSERTIONS (to be executed by external team):")
print("=" * 80)
for i, assertion in enumerate(assertions, 1):
    print(f"\n[Assertion {i}]")
    print(assertion)
    print("-" * 80)

with open("assertions.json", "w") as f:
    import json

    json.dump(assertions, f, indent=4)
