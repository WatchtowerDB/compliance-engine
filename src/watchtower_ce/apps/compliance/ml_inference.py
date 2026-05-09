import logging
from typing import Iterator, List

from django.conf import settings

from .sql_execution import (
    _detect_scheme,
    _execute_mysql,
    _execute_psql,
    _execute_sqlite,
)

if settings.USE_MOCK_COMPLIANCE_CHECKER:
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
        settings.SUPPRESS_MOCK_COMPLIANCE_CHECKER_WARNING
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
_CHECKER_KWARGS = {
    "base_model_path": settings.BASE_MODEL_PATH,
    "chroma_dir": settings.CHROMA_DIR,
    "embedding_model": settings.EMBEDDING_MODEL_DIR,
    "context_window": 131072,  # Set lower if you set `fa` to `False` or `swa_full` to `True` since both increase VRAM usage.
    "n_gpu_layers": -1,
    "prompt_template": "<|turn>user\n{prompt}<turn|>\n<|turn>model\n",
    "stop": ["<turn|>"],
    "top_k": 64,  #  lower slightly if facing VRAM constraints.
    "fa": True,
    "swa_full": False,
}
_EXECUTION_STRATEGIES = {
    "postgres": _execute_psql,
    "postgresql": _execute_psql,
    "sqlite": _execute_sqlite,
    "mysql": _execute_mysql,
}


def get_checker_instance(framework_name: str) -> ComplianceChecker:
    """Return the appropriate compliance checker for the given framework name.

    Resolves the checker class and Chroma collection from the framework registry,
    then instantiates and returns a checker using the shared model configuration.

    Args:
        framework_name (str): The compliance framework identifier, e.g. ``"PCI-DSS"``
            or ``"GDPR"``. Must match a key in ``_FRAMEWORK_REGISTRY`` and corresponds
            to ``ComplianceFramework.name`` in the Django model.

    Returns:
        ComplianceChecker: An instance of the framework-specific checker.

    Raises:
        ValueError: If ``framework_name`` is not found in the registry.
    """
    entry = _FRAMEWORK_REGISTRY.get(framework_name)
    if not entry:
        supported = list(_FRAMEWORK_REGISTRY.keys())
        raise ValueError(
            f"Unsupported compliance framework: '{framework_name}'. "
            f"Supported frameworks: {supported}"
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
    """Generate SQL compliance assertions from schema metadata.

    This function represents the ML / rules-based inference layer.
    It analyzes a serialized database schema and produces SQL assertion
    queries that can be executed independently against the client database.

    Args:
        schema (str): Serialized database schema (e.g., SQL DDL, JSON).
        framework_name (str): The compliance framework to generate assertions for,
            e.g. ``"PCI-DSS"`` or ``"GDPR"``.

    Returns:
        List[str]: A list of SQL assertion queries.
    """
    try:
        schema_str = schema if isinstance(schema, str) else str(schema)
        if not schema_str.strip():
            return []

        assertions = get_checker_instance(framework_name).generate_assertions(
            schema_str
        )

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

        executor_func = _EXECUTION_STRATEGIES.get(db_scheme)

        if executor_func:
            return executor_func(connection_string, sql_query)
        else:
            logger.error("Unsupported database scheme: %s", db_scheme)
            return False, ""

    except Exception as exc:
        logger.exception("Execution Error [%s]: %s", db_scheme, exc)
        return False, ""


def analyze_failed_assertion(
    assertion: str, failure_result: str, framework_name: str
) -> Iterator | str:
    """Analyze a failed SQL assertion and generate remediation guidance.

    This function represents the ML / LLM-based reasoning layer that explains
    why an assertion failed and how to remediate the compliance violation.

    Args:
        assertion (str): The SQL assertion that failed.
        failure_result (str): Execution error or failure output.
        framework_name (str): The compliance framework to use when generating
            remediation guidance, e.g. ``"PCI-DSS"`` or ``"GDPR"``.

    Returns:
        Iterator[CreateCompletionStreamResponse] | str: A streaming iterator of
            LLM response chunks, or a plain string on non-streaming paths.

    Raises:
        ValueError: If the ML engine raises an unexpected error.
    """
    try:
        stream_chunks = get_checker_instance(framework_name).analyze_failed_assertion(
            assertion, failure_result
        )

        return stream_chunks

    except Exception as e:
        raise ValueError("ML Engine Failure (analyze_failed_assertion): %s", e)
