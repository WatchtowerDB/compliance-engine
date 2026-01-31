import redis
import logging
import datetime
import uuid
from . import models
from . import ml_inference as ml
from django.conf import settings
from cloudevents.http import CloudEvent
from cloudevents.conversion import to_structured
from celery import shared_task, chain, chord, group

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)


def publish_event(
    check_id: int, event_type_suffix: str, data: dict, subject: str = None
):
    """
    Publishes a CloudEvent (v1.0.2) to Redis using the official Python SDK.

    Process:
    1. Define Attributes: Sets up standard header fields (specversion, type, source, id, time, datacontenttype)
       and conditionally adds optional fields (e.g., subject) if they exist.
    2. Create CloudEvent: Instantiates the event object, which triggers SDK validation of the attributes.
    3. Serialize: Converts the event to JSON (structured mode), discarding headers to retain only the body.
    4. Publish: Pushes the serialized JSON body to the Redis channel 'check_updates_{check_id}'.
    """

    attributes = {
        "specversion": "1.0",
        "type": f"com.watchtower.compliance.{event_type_suffix}",
        "source": f"/compliance/checks/{check_id}",
        "id": str(uuid.uuid4()),
        "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "datacontenttype": "application/json",
    }

    if subject:
        attributes["subject"] = subject

    event = CloudEvent(attributes, data)

    _, body = to_structured(event)

    channel = f"check_updates_{check_id}"
    redis_client.publish(channel, body)


@shared_task
def initialize_model_task():
    """
    Initializes the PCI Compliance Checker model.
    This runs in the Celery worker process.

    Configuration:
    - Uses value 0 as the default channel number for initialization events.
    """
    publish_event(
        0,
        "phase.update",
        {
            "step": "model_initialization",
            "status": "started",
            "message": "Initializing PCI Compliance Model...",
        },
    )

    if ml.is_model_loaded():
        publish_event(
            0,
            "phase.update",
            {
                "step": "model_initialization",
                "status": "completed",
                "message": "Model already loaded.",
            },
        )
        return

    try:
        ml.get_pci_checker_instance()
        publish_event(
            0,
            "phase.update",
            {
                "step": "model_initialization",
                "status": "completed",
                "message": "Model initialized successfully.",
            },
        )

    except Exception as e:
        logger.exception("Model initialization failed")
        publish_event(
            0,
            "pipeline.error",
            {"step": "model_initialization", "error": str(e)},
        )


@shared_task
def infer_sql_assertions_task(
    schema_id: int, client_db_id: int, framework_id: int, check_id: int
) -> list[int]:
    """
    Infer SQL compliance assertions for a database schema.
    Returns a list of created assertion IDs.

    Workflow:
    1. Protocol: Publishes a 'phase.update' event to signal the start of the assertion generation step.
    2. Retrieval: Fetches the schema and framework objects; handles missing data errors.
    3. Generation: Uses ML to generate SQL assertions based on the schema JSON.
    4. Persistence: Creates ComplianceAssertion records, ensuring each is explicitly linked to the compliance check.
    5. Protocol: Publishes a completion 'phase.update' event including the count of generated assertions.
    """

    publish_event(
        check_id,
        "phase.update",
        {
            "step": "assertion_generation",
            "status": "started",
            "message": "Analyzing schema to generate SQL assertions...",
        },
    )

    try:
        schema = models.ClientDBSchema.objects.get(id=schema_id)
        framework = models.ComplianceFramework.objects.get(id=framework_id)
    except (
        models.ClientDBSchema.DoesNotExist,
        models.ComplianceFramework.DoesNotExist,
    ) as e:
        publish_event(
            check_id,
            "pipeline.error",
            {"check_id": check_id, "step": "assertion_generation", "error": str(e)},
        )
        return []

    try:
        sql_assertions = ml.generate_assertions(schema.schema_json)

        assertion_ids = [
            models.ComplianceAssertion.objects.create(
                schema=schema,
                client_db_id=client_db_id,
                compliance_framework=framework,
                sql_query=sql,
                compliance_check_id=check_id,
            ).id
            for sql in sql_assertions
        ]

        publish_event(
            check_id,
            "phase.update",
            {
                "step": "assertion_generation",
                "status": "completed",
                "assertion_count": len(assertion_ids),
            },
        )

        return assertion_ids

    except Exception as e:
        logger.exception("Failed to generate assertions")
        publish_event(
            check_id,
            "pipeline.error",
            {"step": "assertion_generation", "error": str(e)},
        )
        raise e


@shared_task
def execute_sql_assertion_task(assertion_id: int, check_id) -> tuple[int, str]:
    """
    Execute a single SQL compliance assertion and store the result.

    Steps:
    1. Retrieval: Fetches the assertion object.
    2. Execution: Runs the SQL query against the client DB, returning a pass/fail status and output details.
    3. Storage: Updates the assertion record with the result and query output.
    4. Protocol: Publishes an 'assertion.result' event (with subject) containing the status.
    """
    try:
        assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    except models.ComplianceAssertion.DoesNotExist:
        logger.warning(
            "ComplianceAssertion %s not found. Skipping execution.",
            assertion_id,
        )
        return assertion_id, ""

    passed, output_str = ml.execute_sql_assertion(
        assertion.client_db.connection_string,
        assertion.sql_query,
    )

    assertion.result = passed
    assertion.query_output = output_str
    assertion.save(update_fields=["result", "query_output"])

    publish_event(
        check_id=check_id,
        event_type_suffix="assertion.result",
        subject=f"assertion/{assertion_id}",
        data={
            "status": "passed" if passed else "failed",
        },
    )

    return assertion_id, output_str


@shared_task
def generate_compliance_recommendation_task(
    assertion_id: int, query_output: str, check_id: int
) -> int | None:
    """
    Stream recommendations for failed assertions.

    Logic:
    1. Filter: Skips processing if the assertion passed (analyzes failures only).
    2. Protocol (Start): Publishes a 'recommendation.stream' start event.
    3. Streaming: Iterates over the ML generator.
       - Note: Assumes chunks are structured objects (stream=True).
       - Publishes 'recommendation.stream' token events for each chunk.
    4. Error Handling: Catches exceptions and publishes 'recommendation.stream' error events.
    5. Persistence: Saves the aggregated recommendation text to the assertion.
    6. Protocol (End): Publishes a 'recommendation.stream' complete event.
    """
    try:
        assertion = models.ComplianceAssertion.objects.get(id=assertion_id)
    except models.ComplianceAssertion.DoesNotExist:
        return None

    if assertion.result is not False:
        return assertion_id

    publish_event(
        check_id,
        "recommendation.stream",
        {"event": "start"},
        subject=f"assertion/{assertion_id}",
    )

    full_recommendation = ""

    try:
        for chunk in ml.analyze_failed_assertion(assertion.sql_query, query_output):
            token = chunk["choices"][0]["text"]  # type: ignore (chunk can be str or something else if stream is False, but it isn't)
            full_recommendation += token

            publish_event(
                check_id,
                "recommendation.stream",
                {"event": "token", "content": token},
                subject=f"assertion/{assertion_id}",
            )

    except Exception as exc:
        logger.exception("Recommendation generation failed")
        publish_event(
            check_id,
            "recommendation.stream",
            {"event": "error", "error": str(exc)},
            subject=f"assertion/{assertion_id}",
        )
        return assertion_id

    assertion.recommendation = full_recommendation
    assertion.save(update_fields=["recommendation"])

    publish_event(
        check_id,
        "recommendation.stream",
        {"event": "complete"},
        subject=f"assertion/{assertion_id}",
    )

    return assertion_id


@shared_task
def generate_recommendations_group(
    assertion_output: list[tuple[int, str]], check_id: int
):
    """
    Callback after all executions are done. Triggers analysis phase.

    Sequence:
    1. Protocol: Publishes a 'phase.update' event marking the execution phase as completed.
    2. Filtering: Identifies failed assertions that require recommendations.
    3. Verification: Re-checks failure status against the database for safety.
    4. Launch: If failures exist, publishes a 'phase.update' start event for analysis
       and launches a Celery group of `generate_compliance_recommendation_task`.
    """
    publish_event(
        check_id, "phase.update", {"step": "execution", "status": "completed"}
    )

    if not assertion_output:
        return []

    failed_ids = [res[0] for res in assertion_output if res[0] is not None]

    failed_assertion_ids = list(
        models.ComplianceAssertion.objects.filter(
            id__in=failed_ids, result=False, recommendation__isnull=True
        ).values_list("id", flat=True)
    )

    filtered_results = [
        (aid, out) for aid, out in assertion_output if aid in failed_assertion_ids
    ]

    if filtered_results:
        publish_event(
            check_id,
            "phase.update",
            {
                "step": "analysis",
                "status": "started",
                "message": f"Generating recommendations for {len(filtered_results)} violations...",
            },
        )

        group(
            generate_compliance_recommendation_task.s(aid, out, check_id)
            for aid, out in filtered_results
        ).apply_async()


@shared_task
def execute_then_recommendations(assertion_ids: list[int], check_id: int):
    """
    Orchestrator: Starts Execution Phase.

    Process:
    1. Protocol: Publishes a 'phase.update' event indicating the execution phase has started.
    2. Workflow: Initiates a Celery Chord.
       - Header: Executes all SQL assertions in parallel via `execute_sql_assertion_task`.
       - Body: Triggers `generate_recommendations_group` once all executions complete.
    """
    if not assertion_ids:
        return []

    publish_event(
        check_id,
        "phase.update",
        {
            "step": "execution",
            "status": "started",
            "message": f"Executing {len(assertion_ids)} assertions against client database...",
        },
    )

    chord(
        header=[
            execute_sql_assertion_task.s(assertion_id, check_id)
            for assertion_id in assertion_ids
        ],
        body=generate_recommendations_group.s(check_id),
    ).apply_async()


@shared_task
def schedule_sql_assertion_pipeline(
    schema_id: int,
    client_db_id: int,
    framework_id: int,
    check_id: int,
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
            check_id,
        ),
        execute_then_recommendations.s(check_id),
    ).apply_async()
