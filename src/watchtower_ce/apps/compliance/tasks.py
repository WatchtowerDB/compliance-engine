from celery import shared_task, chain, chord, group
from . import models
from .ml_inference import (
    infer_sql_assertions,
    execute_sql_assertion,
    generate_compliance_recommendations,
)


@shared_task
def infer_sql_assertions_task(schema_id: int, client_db_id: int) -> list[int]:
    """
    Infer SQL compliance assertions for a database schema.
    Returns a list of created assertion IDs.
    """
    schema = models.ClientDBSchema.objects.get(id=schema_id)
    sql_assertions = infer_sql_assertions(schema)

    assertion_ids = [
        models.ComplianceAssertion.objects.create(
            schema_id=schema_id, client_db_id=client_db_id, sql_query=sql
        ).id
        for sql in sql_assertions
    ]

    return assertion_ids


@shared_task
def execute_sql_assertion_task(assertion_id: int) -> int:
    """Execute a single SQL compliance assertion and store the result."""
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    result = execute_sql_assertion(
        assertion.client_db.connection_string, assertion.sql_query
    )
    assertion.result = result
    assertion.save(update_fields=["result"])
    return assertion_id


@shared_task
def generate_compliance_recommendation_task(assertion_id: int) -> int:
    """Generate a recommendation for a single assertion."""
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    assertion.recommendation = generate_compliance_recommendations(assertion.sql_query)
    assertion.save(update_fields=["recommendation"])
    return assertion_id


@shared_task
def generate_recommendations_group(assertion_ids: list[int]):
    """Generate recommendations for multiple assertions in parallel."""
    if not assertion_ids:
        return []
    job = group(generate_compliance_recommendation_task.s(aid) for aid in assertion_ids)
    job.apply_async()


@shared_task
def execute_then_recommendations(assertion_ids: list[int]):
    """
    Execute all assertions in parallel, then generate recommendations.
    This task is used as the second step in the pipeline.
    """
    if not assertion_ids:
        return []

    chord(
        header=[execute_sql_assertion_task.s(aid) for aid in assertion_ids],
        body=generate_recommendations_group.s(),
    ).apply_async()


@shared_task
def schedule_sql_assertion_pipeline(schema_id: int, client_db_id: int):
    """
    Full compliance pipeline:
    1. Infer assertions
    2. Execute all assertions
    3. Generate recommendations
    """

    workflow = chain(
        infer_sql_assertions_task.s(schema_id, client_db_id),
        execute_then_recommendations.s(),
    )
    workflow.apply_async()
