import datetime
import json

import redis
from django.conf import settings
from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import models, serializers
from .filters import (
    ClientDBSchemaFilter,
    ComplianceAssertionFilter,
    ClientDBFilter,
    ComplianceFrameworkFilter,
    ComplianceCheckFilter,
)
from .tasks import initialize_model_task, schedule_sql_assertion_pipeline


@extend_schema_view(
    list=extend_schema(
        summary="List compliance frameworks",
        description="Return a list of all available compliance frameworks. Supports filtering by name and description.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a compliance framework",
        description="Return the details of a specific compliance framework by ID.",
    ),
)
class ComplianceFrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet = models.ComplianceFramework.objects.all()
    serializer_class = serializers.ComplianceFrameworkSerializer
    filterset_class = ComplianceFrameworkFilter


@extend_schema_view(
    list=extend_schema(
        summary="List client databases",
        description="Return a list of all registered client databases. Supports filtering by name.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a client database",
        description="Return the details of a specific client database by ID.",
    ),
    create=extend_schema(
        summary="Register a client database",
        description="Create a new client database entry.",
    ),
    update=extend_schema(
        summary="Replace a client database",
        description="Replace all fields of a client database entry.",
    ),
    partial_update=extend_schema(
        summary="Partially update a client database",
        description="Update one or more fields of a client database entry.",
    ),
    destroy=extend_schema(
        summary="Delete a client database",
        description="Remove a client database entry.",
    ),
)
class ClientDBViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ClientDB.objects.all()
    serializer_class = serializers.ClientDBSerializer
    filterset_class = ClientDBFilter


@extend_schema_view(
    list=extend_schema(
        summary="List database schemas",
        description="Return a list of all client database schemas.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a database schema",
        description="Return the details of a specific database schema by ID.",
    ),
    create=extend_schema(
        summary="Create a database schema",
        description=(
            "Create a new database schema entry directly via JSON. "
            "To upload a `.sql` file instead, use the `upload-schema` action."
        ),
    ),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)
class ClientDBSchemaViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ClientDBSchema.objects.all().order_by("-created_at")
    serializer_class = serializers.ClientDBSchemaSerializer
    filterset_class = ClientDBSchemaFilter

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Update not allowed."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Partial update not allowed."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Delete not allowed."}, status=405)

    @extend_schema(
        request=serializers.ClientDBSchemaUploadSerializer,
        responses={
            201: serializers.ClientDBSchemaSerializer,
            400: OpenApiResponse(
                description="Validation error — invalid file or missing fields."
            ),
        },
        summary="Upload a SQL schema file",
        description=(
            "Upload a `.sql` file to create a new `ClientDBSchema` record. "
            "Expects multipart form data with a `sql_file` field and a `client_db` ID. "
            "All validation is handled by `ClientDBSchemaUploadSerializer`."
        ),
    )
    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="upload-schema",
    )
    def upload_schema(self, request):
        serializer = serializers.ClientDBSchemaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schema = serializer.save()

        response_serializer = self.get_serializer(schema)
        return Response(
            {
                "message": "Schema uploaded successfully.",
                "schema": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(
        summary="List compliance assertions",
        description=(
            "Return a filtered list of compliance assertions. "
            "Supports filtering by schema, client database, and compliance framework."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve a compliance assertion",
        description="Return the details of a specific compliance assertion by ID.",
    ),
)
class ComplianceAssertionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet = models.ComplianceAssertion.objects.select_related(
        "schema", "client_db", "compliance_framework"
    )
    serializer_class = serializers.ComplianceAssertionSerializer
    filterset_class = ComplianceAssertionFilter


@extend_schema_view(
    list=extend_schema(
        summary="List compliance checks",
        description="Return a list of all compliance checks.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a compliance check",
        description="Return the details of a specific compliance check by ID.",
    ),
    create=extend_schema(
        summary="Submit a compliance check",
        description=(
            "Submit a new compliance check. Saves the record and immediately triggers "
            "an asynchronous Celery pipeline to evaluate assertions against the selected "
            "schema, client database, and compliance framework. "
            "Returns a confirmation message and the ID of the created check. "
            "Track processing progress via the `stream-check-updates` SSE endpoint."
        ),
        responses={
            201: OpenApiResponse(
                description="Compliance check created. Returns message and check ID."
            ),
            400: OpenApiResponse(description="Validation error."),
        },
    ),
)
class ComplianceCheckViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ComplianceCheck.objects.all().order_by("-date")
    serializer_class = serializers.ComplianceCheckSerializer
    http_method_names: list[str] = ["get", "post", "head", "options"]
    filterset_class = ComplianceCheckFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check = serializer.save(user=request.user)

        schedule_sql_assertion_pipeline.delay(
            schema_id=check.schema.id,
            client_db_id=check.client_db.id,
            framework_id=check.framework.id,
            check_id=check.id,
        )

        return Response(
            {
                "message": "Compliance check created. Assertions are processing.",
                "id": check.id,
            },
            status=201,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Server-Sent Events stream (text/event-stream)."
        ),
        404: OpenApiResponse(description="Compliance check not found."),
    },
    summary="Stream compliance check updates",
    description=(
        "SSE endpoint that streams real-time processing updates for a specific compliance check.\n\n"
        "**Workflow:**\n"
        "1. Validates that the `ComplianceCheck` with the given `check_id` exists (404 if not).\n"
        "2. If the pipeline has already completed (all failed assertions have recommendations), "
        "immediately emits a `com.watchtower.system.status` completion event and closes the stream.\n"
        "3. Otherwise, subscribes to the Redis pub/sub channel `check_updates_{check_id}` "
        "and emits a `com.watchtower.system.connection` event to confirm the connection.\n"
        "4. Streams all subsequent Redis messages as CloudEvents until the client disconnects.\n\n"
        "Requires authentication."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stream_check_updates(request, check_id):
    get_object_or_404(models.ComplianceCheck, pk=check_id)

    def event_stream():
        failed_assertions = models.ComplianceAssertion.objects.filter(
            compliance_check_id=check_id, result=False
        )

        if (
            failed_assertions.exists()
            and not failed_assertions.filter(recommendation__isnull=True).exists()
        ):
            completion_event = {
                "specversion": "1.0",
                "type": "com.watchtower.system.status",
                "source": "/system/sse",
                "id": "init-complete",
                "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "data": {
                    "status": "completed",
                    "message": "Analysis previously finished.",
                },
            }
            yield f"data: {json.dumps(completion_event)}\n\n"
            return

        r = redis.from_url(settings.CELERY_BROKER_URL)
        pubsub = r.pubsub()
        channel_name = f"check_updates_{check_id}"

        pubsub.subscribe(channel_name)

        try:
            initial_event = {
                "specversion": "1.0",
                "type": "com.watchtower.system.connection",
                "source": "/system/sse",
                "id": "init-1",
                "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "data": {"status": "connected"},
            }
            yield f"data: {json.dumps(initial_event)}\n\n"

            for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield f"data: {data}\n\n"
        finally:
            pubsub.unsubscribe(channel_name)
            r.close()

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Server-Sent Events stream (text/event-stream)."
        ),
    },
    summary="Stream model initialization status",
    description=(
        "SSE endpoint that triggers and streams the status of the AI model initialization process.\n\n"
        "**Workflow:**\n"
        "1. Subscribes to the global Redis pub/sub channel `check_updates_0`.\n"
        "2. Emits a `com.watchtower.system.connection` event to confirm the connection.\n"
        "3. Triggers the `initialize_model_task` Celery task asynchronously.\n"
        "4. Streams status messages from Redis. The stream closes automatically upon receiving "
        "a terminal status: `initialized`, `already_initialized`, or `error`.\n\n"
        "Requires authentication."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stream_model_init(request):
    def event_stream():
        r = redis.from_url(settings.CELERY_BROKER_URL)
        pubsub = r.pubsub()
        channel_name = "check_updates_0"
        pubsub.subscribe(channel_name)

        try:
            initial_event = {
                "specversion": "1.0",
                "type": "com.watchtower.system.connection",
                "source": "/system/sse",
                "id": "init-model",
                "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "data": {"status": "connected"},
            }
            yield f"data: {json.dumps(initial_event)}\n\n"

            initialize_model_task.delay()

            for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    try:
                        payload = json.loads(data)
                        # renamed from `status` to avoid shadowing `rest_framework.status`
                        event_status = payload.get("status")

                        yield f"data: {data}\n\n"

                        if event_status in [
                            "initialized",
                            "already_initialized",
                            "error",
                        ]:
                            break
                    except json.JSONDecodeError:
                        yield f"data: {data}\n\n"
        finally:
            pubsub.unsubscribe(channel_name)
            r.close()

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
