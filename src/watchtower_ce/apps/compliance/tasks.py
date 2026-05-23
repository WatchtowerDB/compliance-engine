import logging
from typing import Optional

from celery import chain, chord, shared_task
from cloudevents.conversion import to_structured
from cloudevents.http import CloudEvent

from . import ml_inference as ml
from . import models
from .redis_client import get_redis
from .sse import RedisSSEStream, build_cloud_event

logger = logging.getLogger(__name__)


def publish_event(
    check_id: int, event_type_suffix: str, data: dict, subject: Optional[str] = None
):
    """
    Publishes a CloudEvent (v1.0) to Redis using the official Python SDK.

    Constructs attributes via build_cloud_event() for consistency with the
    system events emitted in sse.py, then re-serializes through the SDK for
    spec-validated structured-mode JSON before writing to Redis.

    Two writes per call:
    - PUBLISH  → wakes any live XREAD-blocking Django generator.
    - XADD     → appends to the durable stream for backlog replay on reconnect.
    """

    source = "/system/model" if check_id == 0 else f"/compliance/checks/{check_id}"

    event_dict = build_cloud_event(
        event_type=f"com.watchtower.compliance.{event_type_suffix}",
        source=source,
        data=data,
        subject=subject,
    )

    # Re-validate and serialize through the official SDK.
    sdk_event = CloudEvent(
        attributes={k: v for k, v in event_dict.items() if k != "data"},
        data=event_dict["data"],
    )
    _, body = to_structured(sdk_event)

    channel = f"check_updates_{check_id}"
    redis_client = get_redis()
    redis_client.publish(channel, body)
    redis_client.xadd(channel, {"data": body})
    redis_client.expire(channel, RedisSSEStream.STREAM_TTL)


@shared_task
def initialize_model_task() -> None:
    """
    Initializes all registered compliance checker models.

    Iterates over every framework in ``ml._FRAMEWORK_REGISTRY`` and eagerly
    instantiates its checker so model weights are loaded into VRAM once at
    worker startup rather than on the first request.

    Uses check_id=0 as the conventional channel for model-init events.
    """
    publish_event(
        0,
        "phase.update",
        {
            "step": "model_initialization",
            "status": "started",
            "message": "Initializing compliance models...",
        },
    )

    failed_frameworks = []

    for framework_name in ml._FRAMEWORK_REGISTRY:
        try:
            logger.info("Initializing checker for framework: %s", framework_name)
            ml.get_checker_instance(framework_name)
            logger.info("Successfully initialized checker for: %s", framework_name)
        except Exception as e:
            logger.exception(
                "Failed to initialize checker for framework '%s'", framework_name
            )
            failed_frameworks.append(framework_name)
            publish_event(
                0,
                "pipeline.error",
                {
                    "step": "model_initialization",
                    "framework": framework_name,
                    "error": str(e),
                },
            )

    if failed_frameworks:
        publish_event(
            0,
            "phase.update",
            {
                "step": "model_initialization",
                "status": "partial",
                "message": (
                    f"Initialization completed with errors. "
                    f"Failed frameworks: {failed_frameworks}"
                ),
            },
        )
    else:
        publish_event(
            0,
            "phase.update",
            {
                "step": "model_initialization",
                "status": "completed",
                "message": "All compliance models initialized successfully.",
            },
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
        logger.warning(
            "ClientDBSchema or ComplianceFramework %s not found. Skipping assertion inference.",
            schema_id,
        )
        publish_event(
            check_id,
            "pipeline.error",
            {"check_id": check_id, "step": "assertion_generation", "error": str(e)},
        )
        return []

    try:
        sql_assertions = ml.generate_assertions(schema.sql_definition, framework.name)

        assertion_ids = [
            models.ComplianceAssertion.objects.create(
                schema=schema,
                client_db_id=client_db_id,
                compliance_framework=framework,
                sql_query=sql,
                compliance_check_id=check_id,
            ).id  # type: ignore[attr-defined]
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
def execute_sql_assertion_task(assertion_id: int, check_id: int) -> tuple[int, str]:
    """
    Execute a single SQL compliance assertion and store the result.

    Steps:
    1. Retrieval: Fetches the assertion object.
    2. Execution: Runs the SQL query against the client DB, returning a pass/fail result and output details.
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
        data={"status": "passed" if passed else "failed"},
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
    3. Streaming: Iterates over the ML generator using the framework name retrieved
       from ``assertion.compliance_framework.name``, so recommendations are always
       grounded in the correct compliance standard.
       - Publishes 'recommendation.stream' token events for each chunk.
    4. Error Handling: Catches exceptions and publishes 'recommendation.stream' error events.
    5. Persistence: Saves the aggregated recommendation text to the assertion.
    6. Protocol (End): Publishes a 'recommendation.stream' complete event.
    """

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

    publish_event(
        check_id,
        "recommendation.stream",
        {"event": "start"},
        subject=f"assertion/{assertion_id}",
    )

    full_recommendation = ""
    framework_name = assertion.compliance_framework.name

    try:
        for chunk in ml.analyze_failed_assertion(
            assertion.sql_query, query_output, framework_name
        ):
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
def finalize_analysis_task(results, check_id: int) -> None:
    """
    Final callback for the analysis phase. Publishes a completion event
    after all recommendation tasks in the chord have finished.
    """
    publish_event(
        check_id,
        "phase.update",
        {
            "step": "analysis",
            "status": "completed",
            "message": "Analysis and recommendation generation finished.",
        },
    )


@shared_task
def generate_recommendations_group(
    assertion_output: list[tuple[int, str]], check_id: int
) -> list | None:
    """
    Callback after all executions are done. Triggers the analysis phase.

    Sequence:
    1. Protocol: Publishes a 'phase.update' event marking the execution phase as completed.
    2. Filtering: Identifies failed assertions that require recommendations.
    3. Verification: Re-checks failure status against the database for safety.
    4. Launch: If failures exist, publishes a 'phase.update' start event for analysis
       and launches a Celery chord of `generate_compliance_recommendation_task`.
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

        chord(
            header=[
                generate_compliance_recommendation_task.s(aid, out, check_id)  # type: ignore[attr-defined]
                for aid, out in filtered_results
            ],
            body=finalize_analysis_task.s(check_id),  # type: ignore[attr-defined]
        ).apply_async()
    else:
        # If no failures exist, the analysis phase is effectively complete immediately
        publish_event(
            check_id, "phase.update", {"step": "analysis", "status": "completed"}
        )


@shared_task
def execute_then_recommendations(
    assertion_ids: list[int], check_id: int
) -> list | None:
    """
    Orchestrator: starts the execution phase.

    Process:
    1. Protocol: Publishes a 'phase.update' event indicating the execution phase has started.
    2. Workflow: Initiates a Celery chord.
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
            execute_sql_assertion_task.s(assertion_id, check_id)  # type: ignore[attr-defined]
            for assertion_id in assertion_ids
        ],
        body=generate_recommendations_group.s(check_id),  # type: ignore[attr-defined]
    ).apply_async()


@shared_task
def schedule_sql_assertion_pipeline(
    schema_id: int,
    client_db_id: int,
    framework_id: int,
    check_id: int,
) -> None:
    """
    Entry point for the full compliance pipeline:
    1. Generate assertions (infer_sql_assertions_task)
    2. Execute assertions (execute_then_recommendations)
    3. Analyze failures and stream recommendations (generate_recommendations_group → chord)
    """
    chain(
        infer_sql_assertions_task.s(  # type: ignore[attr-defined]
            schema_id,
            client_db_id,
            framework_id,
            check_id,
        ),
        execute_then_recommendations.s(check_id),  # type: ignore[attr-defined]
    ).apply_async()
