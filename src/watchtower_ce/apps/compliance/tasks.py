from celery import shared_task, chain, group

from . import models
from .ml_inference import (
    infer_sql_assertions,
    execute_sql_assertion,
    generate_compliance_recommendations,
)


@shared_task
def infer_sql_assertions_task(schema_id: int, client_db_id: int) -> list[int]:
    """Infer SQL compliance assertions .

    Args:
        schema_id (int): ID of the client database schema.
        client_db_id (int): ID of the client database.

    Returns:
        list[int]: IDs of created ComplianceAssertion records.
    """
    schema = models.ClientDBSchema.objects.get(id=schema_id)

    sql_assertions = infer_sql_assertions(schema)

    assertion_ids: list[int] = []

    for sql in sql_assertions:
        assertion = models.ComplianceAssertion.objects.create(
            schema_id=schema_id,
            client_db_id=client_db_id,
            sql_query=sql,
        )
        assertion_ids.append(assertion.id)

    return assertion_ids


@shared_task
def execute_sql_assertion_task(assertion_id: int) -> int:
    """Execute a single SQL assertion and store the result."""
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)

    result = execute_sql_assertion(
        assertion.client_db.connection_string,
        assertion.sql_query,
    )

    assertion.result = result
    assertion.save(update_fields=["result"])

    return assertion_id


@shared_task
def execute_sql_assertions_group(assertion_ids: list[int]):
    """Execute SQL assertions in parallel."""
    return group(
        execute_sql_assertion_task.s(assertion_id) for assertion_id in assertion_ids
    )()


@shared_task
def generate_compliance_recommendation_task(assertion_id: int) -> int:
    """Generate remediation recommendation for a failed assertion."""
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)

    recommendation = generate_compliance_recommendations(assertion.sql_query)

    assertion.recommendation = recommendation
    assertion.save(update_fields=["recommendation"])

    return assertion_id


@shared_task
def schedule_sql_assertion_pipeline(schema_id: int, client_db_id: int):
    """Run full SQL compliance pipeline: inference → execution."""

    workflow = chain(
        infer_sql_assertions_task.s(schema_id, client_db_id),
        execute_sql_assertions_group.s(),
    )

    workflow.apply_async()
