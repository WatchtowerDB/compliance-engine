import logging
from typing import Iterator, List

from django.conf import settings

from .sql_execution import ExecutorFactory

if settings.LLM_USE_MOCK_COMPLIANCE_CHECKER:
    from ...engine.utils.mock_compliance_checker import (
        MockComplianceChecker as ComplianceChecker,
    )
    from ...engine.utils.mock_compliance_checker import (
        MockComplianceChecker as GDPRComplianceChecker,
    )
    from ...engine.utils.mock_compliance_checker import (
        MockComplianceChecker as PCIComplianceChecker,
    )

    PCIComplianceChecker.suppress_mock_warning = (
        settings.LLM_SUPPRESS_MOCK_COMPLIANCE_CHECKER_WARNING
    )
else:
    from ...engine.core.compliance_checker import ComplianceChecker
    from ...engine.standards.gdpr_compliance_checker import GDPRComplianceChecker
    from ...engine.standards.pci_compliance_checker import PCIComplianceChecker


logger = logging.getLogger(__name__)


_FRAMEWORK_REGISTRY: dict[str, dict] = {
    "PCI-DSS": {
        "checker_class": PCIComplianceChecker,
        "collection_name": "PCI-DSS-v4.0.1",
    },
    "GDPR": {
        "checker_class": GDPRComplianceChecker,
        "collection_name": "GDPR",
    },
}
_CHECKER_KWARGS: dict = {
    "chroma_dir": settings.CHROMA_DIR,
    "embedding_model": settings.EMBEDDING_MODEL_DIR,
    "prompt_template": "<|turn>user\n{prompt}<turn|>\n<|turn>model\n",
    "stop": ["<turn|>"],
    "top_k": 64,  #  lower slightly if facing VRAM constraints.
}


def get_checker_instance(framework_name: str) -> ComplianceChecker:
    """
    Return the appropriate compliance checker for the given framework name.

    Resolves the checker class and Chroma collection from the framework
    registry, then instantiates a checker using the shared generation
    configuration.

    Args:
        framework_name (str): The compliance framework identifier, e.g.
            `"PCI-DSS"` or `"GDPR"`. Must match a key in
            `_FRAMEWORK_REGISTRY` and corresponds to
            `ComplianceFramework.name` in the Django model.

    Returns:
        ComplianceChecker: An instance of the framework-specific checker.

    Raises:
        ValueError: If `framework_name` is not found in the registry.
    """
    entry = _FRAMEWORK_REGISTRY.get(framework_name)
    if not entry:
        raise ValueError(
            f"Unsupported compliance framework: '{framework_name}'. "
            f"Supported frameworks: {list(_FRAMEWORK_REGISTRY.keys())}"
        )

    checker_class: type[ComplianceChecker] = entry["checker_class"]
    collection_name: str = entry["collection_name"]

    logger.debug(
        "Instantiating %s for framework '%s' (collection: %s)",
        checker_class.__name__,
        framework_name,
        collection_name,
    )

    return checker_class(collection_name=collection_name, **_CHECKER_KWARGS)


def generate_assertions(schema: str, framework_name: str) -> List[str]:
    """
    Generate SQL compliance assertions from a database schema.

    Analyzes a serialized database schema and produces SQL assertion queries
    that can be executed independently against the client database to detect
    compliance violations.

    Args:
        schema (str): Serialized database schema (e.g., SQL DDL).
        framework_name (str): The compliance framework to generate assertions
            for, e.g. `"PCI-DSS"` or `"GDPR"`.

    Returns:
        List[str]: A list of SQL assertion queries. Empty on failure.
    """
    try:
        schema_str = schema if isinstance(schema, str) else str(schema)
        if not schema_str.strip():
            return []
        return get_checker_instance(framework_name).generate_assertions(schema_str)
    except Exception as e:
        logger.exception("Failed to generate assertions via ML engine: %s", e)
        return []


def execute_sql_assertion(connection_string: str, sql_query: str) -> tuple[bool, str]:
    """
    Execute a SQL assertion against a client database.

    Runs a single SQL assertion query and evaluates whether it passes or
    fails. Queries that do not begin with `SELECT` or `WITH` are blocked
    as a safety measure against destructive statements.

    Args:
        connection_string (str): Database connection string.
        sql_query (str): SQL assertion query to execute.

    Returns:
        tuple[bool, str]: `(True, "")` if the assertion passes (no rows
            returned), `(False, result)` otherwise.
    """
    clean_query = sql_query.strip().upper()
    if not clean_query.startswith("SELECT") and not clean_query.startswith("WITH"):
        logger.error("Blocked potentially unsafe query: %s", sql_query)
        return False, ""

    try:
        executor = ExecutorFactory.get_executor(connection_string)
        return executor.execute(sql_query)
    except ValueError as val_err:
        logger.error(str(val_err))
        return False, ""
    except Exception as exc:
        logger.exception("Execution Error: %s", exc)
        return False, ""


def analyze_failed_assertion(
    assertion: str, failure_result: str, framework_name: str
) -> Iterator:
    """
    Analyze a failed SQL assertion and stream remediation guidance.

    Uses the LLM to explain why an assertion failed and provide concrete
    remediation steps grounded in the relevant compliance standard.

    Args:
        assertion (str): The SQL assertion that failed.
        failure_result (str): The rows or error output returned by the assertion.
        framework_name (str): The compliance framework to use when generating
            remediation guidance, e.g. `"PCI-DSS"` or `"GDPR"`.

    Returns:
        Iterator: A streaming iterator of LLM response chunks. Each chunk
            exposes `chunk["choices"][0]["text"]`.

    Raises:
        ValueError: If the ML engine raises an unexpected error.
    """
    try:
        return get_checker_instance(framework_name).analyze_failed_assertion(
            assertion, failure_result
        )

    except Exception as e:
        raise ValueError("ML Engine Failure (analyze_failed_assertion): %s" % e)
