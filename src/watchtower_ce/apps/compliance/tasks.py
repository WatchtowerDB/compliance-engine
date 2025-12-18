from celery import shared_task, group
from . import models
from .ml_inference import (
    run_sql_assertion_inference,
    generate_compliance_recommendations,
)


@shared_task
def schedule_sql_assertions_inference(schema_id=None, client_db_id=None):
    assertions = models.ComplianceAssertion.objects.filter(result__isnull=True)
    if schema_id:
        assertions = assertions.filter(schema_id=schema_id)
    if client_db_id:
        assertions = assertions.filter(client_db_id=client_db_id)

    task_group = group(run_sql_assertion_task.s(a.id) for a in assertions)
    task_group.apply_async()
    return f"Scheduled {assertions.count()} SQL assertion tasks."


@shared_task
def run_sql_assertion_task(assertion_id):
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    result = run_sql_assertion_inference(
        assertion.client_db.connection_string, assertion.sql_query
    )
    assertion.result = result
    assertion.save()
    return f"Assertion {assertion_id} done."


@shared_task
def schedule_compliance_recommendation(schema_id=None, client_db_id=None):
    violations = models.ComplianceAssertion.objects.filter(result=False)
    if schema_id:
        violations = violations.filter(schema_id=schema_id)
    if client_db_id:
        violations = violations.filter(client_db_id=client_db_id)

    task_group = group(run_compliance_recommendation_task.s(v.id) for v in violations)
    task_group.apply_async()
    return f"Scheduled {violations.count()} recommendation tasks."


@shared_task
def run_compliance_recommendation_task(assertion_id):
    assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    recommendation = generate_compliance_recommendations(assertion.sql_query)
    assertion.recommendation = recommendation
    assertion.save()
    return f"Recommendation generated for {assertion_id}"
