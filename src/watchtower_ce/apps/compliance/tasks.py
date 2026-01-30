from celery import shared_task, chain, chord, group
import logging
from . import models
from . import ml_inference as ml

logger = logging.getLogger(__name__)


@shared_task
def infer_sql_assertions_task(
    schema_id: int,
    client_db_id: int,
    framework_id: int,
) -> list[int]:
    """
    Infer SQL compliance assertions for a database schema.
    Returns a list of created assertion IDs.
    """
    try:
        schema = models.ClientDBSchema.objects.get(id=schema_id)
    except models.ClientDBSchema.DoesNotExist:
        logger.warning(
            "ClientDBSchema %s not found. Skipping assertion inference.",
            schema_id,
        )
        return []

    try:
        framework = models.ComplianceFramework.objects.get(id=framework_id)
    except models.ComplianceFramework.DoesNotExist:
        logger.warning(
            "ComplianceFramework %s not found. Skipping assertion inference.",
            framework_id,
        )
        return []

    sql_assertions = ml.generate_assertions(schema.schema_json)

    assertion_ids = [
        models.ComplianceAssertion.objects.create(
            schema=schema,
            client_db_id=client_db_id,
            compliance_framework=framework,
            sql_query=sql,
        ).id
        for sql in sql_assertions
    ]

    return assertion_ids


@shared_task
def execute_sql_assertion_task(assertion_id: int) -> tuple[int, str]:
    """
    Execute a single SQL compliance assertion and store the result.
    """
    try:
        assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    except models.ComplianceAssertion.DoesNotExist:
        logger.warning(
            "ComplianceAssertion %s not found. Skipping execution.",
            assertion_id,
        )
        return assertion_id, ""

    result = ml.execute_sql_assertion(
        assertion.client_db.connection_string,
        assertion.sql_query,
    )

    assertion.result = result[0]
    assertion.save(update_fields=["result"])

    return assertion_id, result[1]


@shared_task
def generate_compliance_recommendation_task(
    assertion_id: int, query_output: str
) -> int | None:
    try:
        assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    except models.ComplianceAssertion.DoesNotExist:
        logger.warning(
            "ComplianceAssertion %s not found. Skipping recommendation task.",
            assertion_id,
        )
        return None

    if assertion.result is not False:
        return assertion_id
    recommendation: str = ""

    try:
        logger.info("Analyzing failed assertion")

        stream_chunks = ml.analyze_failed_assertion(
            assertion.sql_query,
            query_output,
        )
        response_tokens = []

        for chunk in stream_chunks:
            token = chunk["choices"][0]["text"]  # type: ignore (chunk can be str or something else if stream is False, but it isn't)
            # TODO: API FUNCTION CALL
            response_tokens.append(token)

        logger.info("Successfully analyzed failed assertion")
        recommendation: str = "".join(response_tokens).strip()

    except ValueError as exc:
        logger.exception(exc)
        raise exc
    except Exception as exc:
        logger.exception(
            "Failed to generate recommendation for assertion %s", assertion_id
        )
        raise exc
    if recommendation:
        pass  # TODO: IMPLEMEMT FALLBACK LOGIC

    assertion.recommendation = recommendation
    assertion.save(update_fields=["recommendation"])

    return assertion_id


@shared_task
def generate_recommendations_group(assertion_output: list[tuple[int, str]]):
    """
    Generate recommendations for multiple assertions in parallel.
    """

    if not assertion_output:
        return []

    failed_assertion_ids = list(
        models.ComplianceAssertion.objects.filter(
            id__in=map(lambda res: res[0], assertion_output),
            result__in=[False, None],
            recommendation__isnull=True,
        ).values_list("id", flat=True)
    )

    filtered_results = filter(
        lambda res: res[0] in failed_assertion_ids, assertion_output
    )

    group(
        generate_compliance_recommendation_task.s(assertion_id, query_output)
        for assertion_id, query_output in filtered_results
    ).apply_async()


@shared_task
def execute_then_recommendations(assertion_ids: list[int]):
    """
    Execute all assertions in parallel, then generate recommendations.
    """
    if not assertion_ids:
        return []

    chord(
        header=[
            execute_sql_assertion_task.s(assertion_id) for assertion_id in assertion_ids
        ],
        body=generate_recommendations_group.s(),
    ).apply_async()


@shared_task
def schedule_sql_assertion_pipeline(
    schema_id: int,
    client_db_id: int,
    framework_id: int,
):
    """
    Full compliance pipeline:
    1. Generate assertions
    2. Execute assertions
    3. Analyze failures
    """
    chain(
        infer_sql_assertions_task.s(
            schema_id,
            client_db_id,
            framework_id,
        ),
        execute_then_recommendations.s(),
    ).apply_async()
