import psycopg
import sqlite3
import logging
from typing import List, Sequence, Any
from urllib.parse import urlparse
from django.conf import settings
from ...engine.scripts.pci_compliance_checker import PCIComplianceChecker

logger = logging.getLogger(__name__)


def get_pci_checker_instance() -> PCIComplianceChecker:
    return PCIComplianceChecker(
        model_path=settings.MODEL_PATH,
        chroma_dir=settings.CHROMA_DIR,
        collection_name="PCI-DSS-v4.0.1",
        context_window=8192,
        n_gpu_layers=31,
    )


def generate_assertions(schema: str) -> List[str]:
    """Generate SQL compliance assertions from schema metadata.

    This function represents the ML / rules-based inference layer.
    It analyzes a serialized database schema and produces SQL
    assertion queries that can be executed independently.

    Args:
        schema (str): Serialized database schema (e.g., SQL DDL, JSON).

    Returns:
        List[str]: A list of SQL assertion queries.
    """

    try:
        schema_str = schema if isinstance(schema, str) else str(schema)
        if not schema_str.strip():
            return []

        assertions = get_pci_checker_instance().generate_assertions(schema_str)

        return assertions

    except Exception as e:
        logger.exception("Failed to generate assertions via ML engine: %s", e)
        return []


def execute_sql_assertion(connection_string: str, sql_query: str) -> tuple[bool, str]:
    """Execute a SQL assertion against a client database.

    This function runs a single SQL assertion query and evaluates
    whether it passes or fails.

    Args:
        connection_string (str): Database connection string.
        sql_query (str): SQL assertion query to execute.

    Returns:
        tuple[bool,str]: True and empty string if the assertion passes, False and query result otherwise.
    """

    clean_query = sql_query.strip().upper()
    if not clean_query.startswith("SELECT") and not clean_query.startswith("WITH"):
        logger.error("Blocked potentially unsafe query: %s", sql_query)
        return False, ""

    try:
        db_scheme = _detect_scheme(connection_string)

        if db_scheme in ("postgres", "postgresql"):
            return _execute_psql(connection_string, sql_query)
        elif db_scheme == "sqlite":
            return _execute_sqlite(connection_string, sql_query)
        else:
            logger.error("Unsupported database scheme: %s", db_scheme)
            return False, ""

    except Exception as exc:
        logger.exception("Execution Error [%s]: %s", db_scheme, exc)
        return False, ""


def analyze_failed_assertion(assertion: str, failure_result: str) -> str:
    """Analyze a failed SQL assertion and generate remediation guidance.

    This function represents the ML / LLM-based reasoning layer that
    explains why an assertion failed and how to fix it.

    Args:
        assertion (str): The SQL assertion that failed.
        failure_result (str): Execution error or failure output.

    Returns:
        str: Human-readable compliance recommendation.
    """

    try:
        recommendation = get_pci_checker_instance().analyze_failed_assertion(
            assertion, failure_result
        )

        return recommendation

    except Exception as e:
        logger.exception("ML Engine Failure (analyze_failed_assertion): %s", e)
        return "Analysis unavailable. Please review the SQL violation manually."


def _execute_psql(conn_str: str, sql_query: str) -> tuple[bool, str]:
    """
    Executes a query against a PostgreSQL database.

    Workflow:
    - Connect -> Cursor -> Execute -> Fetch -> Close (handled by context managers).
    - If query returns rows, check if they indicate a pass/fail.
    - No rows returned usually means passed for assertions.
    """
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
    """
    Executes a query against a SQLite database.

    Implementation Details:
    - Handles 'sqlite:///path' vs 'path' formats by stripping the prefix.
    - SQLite needs strict read-only mode if possible, but standard connect is
      acceptable provided we enforce SELECT-only in the calling function.
    """
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


def _detect_scheme(conn_str: str) -> str:
    """
    Detect database type from connection string.

    Logic:
    - Prefer explicit URL schemes via urlparse.
    - Only use SQLite file extension heuristics when no scheme is present and the
      string does not look like a URL.
    - Includes fallback logic for Psycopg DSNs (e.g., 'host=localhost user=admin').
    """
    normalized = conn_str.strip()
    lower = normalized.lower()
    parsed = urlparse(normalized)
    if parsed.scheme:
        if parsed.scheme in ("sqlite", "sqlite3"):
            return "sqlite"
        return parsed.scheme

    if "://" not in normalized and lower.endswith((".db", ".sqlite", ".sqlite3")):
        return "sqlite"

    if any(k in conn_str for k in ("host=", "dbname=", "user=")):
        return "postgresql"


def _passes(rows: Sequence[Sequence[Any]]) -> bool:
    """
    Evaluate assertion result.

    Convention:
    - Empty result set = PASS (No violations found).
    - Rows returned = FAIL (Violations found).
    - Single row with 0/False = PASS (Specifically handles 'SELECT COUNT(*)' cases).
    - Default: Any other returned violation rows mean failure.
    """
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
