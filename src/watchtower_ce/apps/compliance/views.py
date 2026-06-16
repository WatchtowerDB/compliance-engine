from typing import cast

from celery.app.task import Task
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    renderer_classes,
)
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import models, serializers
from .filters import (
    ClientDBFilter,
    ClientDBSchemaFilter,
    ComplianceAssertionFilter,
    ComplianceCheckFilter,
    ComplianceFrameworkFilter,
)
from .renderers import SSERenderer
from .sse import RedisSSEStream, build_cloud_event, format_sse
from .tasks import initialize_model_task, schedule_sql_assertion_pipeline


@extend_schema_view(
    list=extend_schema(
        summary="List compliance frameworks",
        description=(
            "Return a list of all available compliance frameworks. "
            "Supports filtering by name and description, searching on both, "
            "and ordering by name or ID."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve a compliance framework",
        description="Return the details of a specific compliance framework by ID.",
    ),
)
class ComplianceFrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ComplianceFramework.objects.all()
    serializer_class = serializers.ComplianceFrameworkSerializer
    filterset_class = ComplianceFrameworkFilter

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = ["name", "description"]
    ordering_fields = ["name", "id"]


@extend_schema_view(
    list=extend_schema(
        summary="List client databases",
        description=(
            "Return a list of all registered client databases. "
            "Supports filtering by name and ordering by name or ID."
        ),
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
    queryset = models.ClientDB.objects.all()
    serializer_class = serializers.ClientDBSerializer
    filterset_class = ClientDBFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "id"]


@extend_schema_view(
    list=extend_schema(
        summary="List database schemas",
        description=(
            "Return a list of all client database schemas. Results default to newest first. "
            "Supports ordering by created_at and id."
        ),
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
    queryset = models.ClientDBSchema.objects.all()
    serializer_class = serializers.ClientDBSchemaSerializer
    filterset_class = ClientDBSchemaFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "id"]

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Update not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Partial update not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Delete not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

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
            "Supports filtering by schema, database, framework, result, and check. "
            "Supports ordering by compliance_check, client_db, result, or id. "
            "Use the `ordering` parameter (e.g., `?ordering=-id`, `ordering=client_db,id`)."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve a compliance assertion",
        description="Return the details of a specific compliance assertion by ID.",
    ),
)
class ComplianceAssertionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ComplianceAssertion.objects.select_related(
        "schema", "client_db", "compliance_framework"
    )
    serializer_class = serializers.ComplianceAssertionSerializer
    filterset_class = ComplianceAssertionFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["compliance_check", "client_db", "result", "id"]


@extend_schema_view(
    list=extend_schema(
        summary="List compliance checks",
        description=(
            "Return a list of all compliance checks. Results default to newest first. "
            "Supports filtering by framework and database, and ordering by date, "
            "framework, client_db, or id."
        ),
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
    queryset = models.ComplianceCheck.objects.all()
    serializer_class = serializers.ComplianceCheckSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_class = ComplianceCheckFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["date", "framework", "client_db", "id"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check = serializer.save(user=request.user)

        cast(Task, schedule_sql_assertion_pipeline).delay(
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
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Retrieve latest compliance check",
        description="Return the most recently created compliance check.",
    )
    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        latest_check = self.get_queryset().last()

        if latest_check is None:
            return Response(
                {"detail": "No compliance checks found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(latest_check)
        return Response(serializer.data)


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
        "immediately emits a `com.watchtower.system.completed` event and closes the stream.\n"
        "3. Otherwise, emits a `com.watchtower.system.connected` event to confirm the connection.\n"
        "4. Replays any events missed since `Last-Event-ID` (if provided), then tails the "
        "Redis stream live via XREAD, forwarding events as CloudEvents until the pipeline "
        "reaches a terminal state.\n\n"
        "Requires authentication."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([SSERenderer])
def stream_check_updates(request, check_id):
    get_object_or_404(models.ComplianceCheck, pk=check_id)

    failed_assertions = models.ComplianceAssertion.objects.filter(
        compliance_check_id=check_id, result=False
    )
    if (
        failed_assertions.exists()
        and not failed_assertions.filter(recommendation__isnull=True).exists()
    ):

        def _done():
            event = build_cloud_event(
                event_type=RedisSSEStream.EVT_COMPLETED,
                source=f"/compliance/checks/{check_id}",
                data={
                    "status": "completed",
                    "message": "Analysis previously finished.",
                },
            )
            yield format_sse(None, event)

        return StreamingHttpResponse(_done(), content_type="text/event-stream")

    last_event_id = request.headers.get("Last-Event-ID")
    sse = RedisSSEStream(f"check_updates_{check_id}")
    return StreamingHttpResponse(
        sse.stream(last_event_id), content_type="text/event-stream"
    )


@extend_schema(
    responses={
        202: OpenApiResponse(description="Model initialization triggered."),
    },
    summary="Trigger model initialization",
    description=(
        "Enqueues the model initialization task so that compliance checker weights "
        "are loaded into memory before the first check is submitted. "
        "Returns immediately; initialization runs asynchronously in the Celery worker.\n\n"
        "Requires authentication.\n"
        "WARNING: THIS ENDPOINT WILL CRASH YOUR BACKEND!\n"
        "IMPLEMENTATION WILL BE CHANGED LATER!\n"
        "For starters, it'll support GET to poll for the model state. "
        "Please recognise that this endpoint is not and will not be "
        "reliable or complete until certain other features are implemented."
    ),
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trigger_model_init(request):
    # TODO: ADD MODEL STATES AFTER NEW SINGLETON IMPLEMENTATION,
    #       GET FOR POLLING, OTHER STATUS CODES, AND UPDATE THE
    #       TASK ITSELF.
    cast(Task, initialize_model_task).delay()
    return Response(
        {"message": "Model initialization enqueued."}, status=status.HTTP_202_ACCEPTED
    )
