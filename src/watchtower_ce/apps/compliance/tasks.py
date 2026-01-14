from celery import shared_task, chain, chord, group
from . import models
from . import ml_inference as ml


@shared_task
def infer_sql_assertions_task(schema_id: int, client_db_id: int) -> list[int]:
    """
    Infer SQL compliance assertions for a database schema.
    Returns a list of created assertion IDs.
    """
    schema = models.ClientDBSchema.objects.get(id=schema_id)

    sql_assertions = ml.generate_assertions(schema.schema_json)

    assertion_ids = [
        models.ComplianceAssertion.objects.create(
            schema_id=schema_id,
            client_db_id=client_db_id,
            sql_query=sql,
        ).id
        for sql in sql_assertions
    ]

    return assertion_ids


@shared_task
def execute_sql_assertion_task(assertion_id: int) -> int:
    """
    Execute a single SQL compliance assertion and store the result.
    """
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)

    result = ml.execute_sql_assertion(
        assertion.client_db.connection_string,
        assertion.sql_query,
    )

    assertion.result = result
    assertion.save(update_fields=["result"])

    return assertion_id


@shared_task
def generate_compliance_recommendation_task(assertion_id: int) -> int:
    """
    Generate a recommendation for a single failed assertion.
    """
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)

    if assertion.result is True:
        return assertion_id

    recommendation = ml.analyze_failed_assertion(
        assertion=assertion.sql_query,
        failure_result=str(assertion.result),
    )

    assertion.recommendation = recommendation
    assertion.save(update_fields=["recommendation"])

    return assertion_id


@shared_task
def generate_recommendations_group(assertion_ids: list[int]):
    """
    Generate recommendations for multiple assertions in parallel.
    """
    if not assertion_ids:
        return []

    failed_assertion_ids = list(
        models.ComplianceAssertion.objects.filter(
            id__in=assertion_ids,
            result=False,
            recommendation__isnull=True,
        ).values_list("id", flat=True)
    )

    group(
        generate_compliance_recommendation_task.s(assertion_id)
        for assertion_id in failed_assertion_ids
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
def schedule_sql_assertion_pipeline(schema_id: int, client_db_id: int):
    """
    Full compliance pipeline:
    1. Generate assertions
    2. Execute assertions
    3. Analyze failures
    """
    chain(
        infer_sql_assertions_task.s(schema_id, client_db_id),
        execute_then_recommendations.s(),
    ).apply_async()
