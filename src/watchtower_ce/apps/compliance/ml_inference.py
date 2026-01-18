import threading
import psycopg
import sqlite3
from typing import List, Sequence, Any, Optional
from urllib.parse import urlparse
import logging
from settings.env import MODEL_PATH, CHROMA_DIR
from engine.scripts.pci_compliance_checker import PCIComplianceChecker

logger = logging.getLogger(__name__)

_PCI_CHECKER: Optional[PCIComplianceChecker] = None
_CHECKER_LOCK = threading.Lock()


def get_pci_checker() -> PCIComplianceChecker:
    """
    Thread-safe singleton accessor for the PCIComplianceChecker.
    Lazily initializes the model on first use.

    Implementation Details:
    - Uses a Double-checked locking pattern for performance to ensure thread safety
      without locking on every access once initialized.
    - Checks the instance again inside the lock to prevent race conditions.
    """
    global _PCI_CHECKER
    
    if _PCI_CHECKER is None:
        with _CHECKER_LOCK:
            if _PCI_CHECKER is None:
                _validate_config()
                
                logger.info(f"Initializing PCIComplianceChecker (Model: {MODEL_PATH.name})...")
                _PCI_CHECKER = PCIComplianceChecker(
                    model_path=MODEL_PATH,
                    chroma_dir=CHROMA_DIR,
                    collection_name="PCI-DSS-v4.0.1"
                )
                logger.info("PCIComplianceChecker initialized successfully.")
        
    return _PCI_CHECKER

def _validate_config() -> None:
    """Ensure environment paths are valid before loading model."""
    if not MODEL_PATH or not MODEL_PATH.exists():
        error_msg = f"Model path invalid: {MODEL_PATH}. Check WTCE_MODEL_PATH in env."
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not CHROMA_DIR or not CHROMA_DIR.exists():
        error_msg = f"ChromaDB path invalid: {CHROMA_DIR}. Check WTCE_CHROMA_DIR in env."
        logger.error(error_msg)
        raise ValueError(error_msg)

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

        checker = get_pci_checker()
        assertions = checker.generate_assertions(schema_str)
        
        return assertions
        
    except Exception as e:
        logger.exception("Failed to generate assertions via ML engine: %s", e)
        return []


def execute_sql_assertion(connection_string: str, sql_query: str) -> bool:
    """Execute a SQL assertion against a client database.

    This function runs a single SQL assertion query and evaluates
    whether it passes or fails.

    Args:
        connection_string (str): Database connection string.
        sql_query (str): SQL assertion query to execute.

    Returns:
        bool: True if the assertion passes, False otherwise.
    """

    clean_query = sql_query.strip().upper()
    if not clean_query.startswith("SELECT") and not clean_query.startswith("WITH"):
        logger.error("Blocked potentially unsafe query: %s", sql_query)
        return False

    try:
        db_scheme = _detect_scheme(connection_string)
        
        if db_scheme in ("postgres", "postgresql"):
            return _execute_psql(connection_string, sql_query)
        elif db_scheme == "sqlite":
            return _execute_sqlite(connection_string, sql_query)
        else:
            logger.error("Unsupported database scheme: %s", db_scheme)
            return False
            
    except Exception as exc:
        logger.exception("Execution Error [%s]: %s", db_scheme, exc)
        return False


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
        checker = get_pci_checker()
        
        recommendation = checker.analyze_failed_assertion(assertion, failure_result)
        
        return recommendation
        
    except Exception as e:
        logger.exception("ML Engine Failure (analyze_failed_assertion): %s", e)
        return "Analysis unavailable. Please review the SQL violation manually."


def _execute_psql(conn_str: str, sql_query: str) -> bool:
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

                if cur.description:
                    rows = cur.fetchall()
                    return _passes(rows)
                return True
    except psycopg.Error as e:
        logger.error("PostgreSQL Operational Error: %s", e)
        return False


def _execute_sqlite(conn_str: str, sql_query: str) -> bool:
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
            cur = conn.cursor()
            cur.execute(sql_query)
            rows = cur.fetchall()
            return _passes(rows)
    except sqlite3.Error as e:
        logger.error("SQLite Operational Error: %s", e)
        return False
    
    
def _detect_scheme(conn_str: str) -> str:
    """
    Detect database type from connection string.
    
    Logic:
    - Checks for SQLite extensions or substrings.
    - Uses urlparse for standard schemes.
    - Includes fallback logic for Psycopg DSNs (e.g., 'host=localhost user=admin').
    """
    if "sqlite" in conn_str.lower() or conn_str.endswith((".db", ".sqlite", ".sqlite3")):
        return "sqlite"
        
    parsed = urlparse(conn_str)
    if parsed.scheme:
        return parsed.scheme
        
    if any(k in conn_str for k in ("host=", "dbname=", "user=")):
        return "postgresql"
        
    return "unknown"


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
        
    first_row = rows[0]
    if len(first_row) == 1 and isinstance(first_row[0], (int, float)):
        return first_row[0] == 0
        
    return False
