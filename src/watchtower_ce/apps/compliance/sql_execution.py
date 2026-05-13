import abc
import logging
import sqlite3
from typing import Any, Sequence
from urllib.parse import urlparse

import psycopg
import MySQLdb

logger = logging.getLogger(__name__)


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


class DatabaseExecutor(abc.ABC):
    """Abstract base interface for database execution strategies."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    @abc.abstractmethod
    def execute(self, sql_query: str) -> tuple[bool, str]:
        """Executes a SQL query and returns (passed, output_str)."""
        pass


class PostgresExecutor(DatabaseExecutor):
    def execute(self, sql_query: str) -> tuple[bool, str]:
        try:
            with psycopg.connect(self.connection_string) as conn:
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


class SQLiteExecutor(DatabaseExecutor):
    def execute(self, sql_query: str) -> tuple[bool, str]:
        db_path = self.connection_string.removeprefix("sqlite:///")
        try:
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute(sql_query)
                passed = True
                rows = []
                if cur.description:
                    rows = cur.fetchmany(3)
                    passed = _passes(rows)
                return passed, str(rows)
        except sqlite3.Error as e:
            logger.error("SQLite Operational Error: %s", e)
            return False, ""


class MySQLExecutor(DatabaseExecutor):
    def execute(self, sql_query: str) -> tuple[bool, str]:
        parsed = urlparse(self.connection_string)
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


class ExecutorFactory:
    """Factory to instantiate the appropriate DatabaseExecutor."""

    @staticmethod
    def get_executor(conn_str: str) -> DatabaseExecutor:
        scheme = ExecutorFactory._detect_scheme(conn_str)

        if scheme in ("postgresql", "postgres"):
            return PostgresExecutor(conn_str)
        if scheme == "sqlite":
            return SQLiteExecutor(conn_str)
        if scheme == "mysql":
            return MySQLExecutor(conn_str)

        raise ValueError(f"Unsupported database scheme detected: '{scheme}'")

    @staticmethod
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

        return ""
