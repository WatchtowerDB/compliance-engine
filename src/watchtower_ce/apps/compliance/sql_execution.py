import logging
import sqlite3
from typing import Any, Sequence
from urllib.parse import urlparse

import psycopg
import MySQLdb

logger = logging.getLogger(__name__)


def _execute_psql(conn_str: str, sql_query: str) -> tuple[bool, str]:
    """Executes a query against a PostgreSQL database."""
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                passed = True
                rows = []
                if cur.description:
                    rows = cur.fetchmany(3)
                    passed = _passes(rows)
                return passed, str(rows)
    except psycopg.Error as e:
        logger.error("PostgreSQL Operational Error: %s", e)
        return False, ""


def _execute_sqlite(conn_str: str, sql_query: str) -> tuple[bool, str]:
    """Executes a query against a SQLite database."""
    db_path = conn_str.removeprefix("sqlite:///")

    try:
        with sqlite3.connect(db_path) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                rows = cur.fetchmany(3)
                passed = _passes(rows)
                return passed, str(rows)
    except sqlite3.Error as e:
        logger.error("SQLite Operational Error: %s", e)
        return False, ""


def _execute_mysql(conn_str: str, sql_query: str) -> tuple[bool, str]:
    """Executes a query against a MySQL database."""
    parsed = urlparse(conn_str)
    conn_kwargs = {
        "host": parsed.hostname or "localhost",
        "user": parsed.username or "root",
        "passwd": parsed.password or "",
        "db": parsed.path.lstrip("/") if parsed.path else "",
        "port": parsed.port or 3306,
    }

    try:
        with MySQLdb.connect(**conn_kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                passed = True
                rows = []
                if cur.description:
                    rows = cur.fetchmany(3)
                    passed = _passes(rows)
                return passed, str(rows)
    except MySQLdb.Error as e:
        logger.error("MySQL Operational Error: %s", e)
        return False, ""


def _detect_scheme(conn_str: str) -> str:
    """Detect database type from connection string."""
    normalized = conn_str.strip()
    lower = normalized.lower()
    parsed = urlparse(normalized)

    if parsed.scheme:
        if parsed.scheme in ("sqlite", "sqlite3"):
            return "sqlite"
        if parsed.scheme in ("mysql", "mysql2"):
            return "mysql"
        return parsed.scheme

    if "://" not in normalized and lower.endswith((".db", ".sqlite", ".sqlite3")):
        return "sqlite"

    if any(k in conn_str for k in ("host=", "dbname=", "user=")):
        return "postgresql"


def _passes(rows: Sequence[Sequence[Any]]) -> bool:
    """Evaluate assertion result."""
    if not rows:
        return True

    if len(rows) > 1:
        return False

    first_row = rows[0]

    if len(first_row) != 1:
        return False

    val = first_row[0]

    if isinstance(val, bool):
        return val is False

    if isinstance(val, (int, float)):
        return val == 0

    return False
