--
-- PostgreSQL database dump
--

\restrict 2s6Pxz2LsFFfhvbBj6a5cBBpiygKfBbZgvw6ml9NzLhZoRc0HdseGLCgp30PGhb

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

\unrestrict 2s6Pxz2LsFFfhvbBj6a5cBBpiygKfBbZgvw6ml9NzLhZoRc0HdseGLCgp30PGhb

