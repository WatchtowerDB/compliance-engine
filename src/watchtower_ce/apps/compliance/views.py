from typing import cast

from celery.app.task import Task
from django.conf import settings
from django.db.models import Count, Max
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers as rest_framework_serializers
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

from ...engine.clients import LLMInference
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
from .tasks import schedule_sql_assertion_pipeline


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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "id", "name"]

    def update(self, request, *args, **kwargs):
        """Updates are not allowed for versioned schemas. Use upload-schema to create a new version."""
        return Response(
            {"detail": "Update not allowed. Create a new version via upload-schema."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """Partial updates are not allowed for versioned schemas."""
        return Response(
            {
                "detail": "Partial update not allowed. Create a new version via upload-schema."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Deletion is not allowed to maintain version history integrity."""
        return Response(
            {"detail": "Deletion not allowed. Schemas are versioned and immutable."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
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
            "Upload a `.sql` file to create a new version of a `ClientDBSchema`. "
            "If a schema with the same `name` and `client_db` exists, the `internal_version` "
            "is automatically incremented. Otherwise, version 1 is created.\n\n"
            "Expects multipart form data with a `sql_file` field, a `client_db` ID, "
            "and a `name`. All validation is handled by `ClientDBSchemaUploadSerializer`.\n\n"
            "**Versioning behavior:**\n"
            "- Same `name` + `client_db` -> new version (internal_version + 1)\n"
            "- Different `name` or `client_db` -> new version 1\n"
            "- Updates and deletes are not allowed to maintain audit integrity."
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
            "Supports filtering by schema, database, framework, result, check and status. "
            "Supports ordering by compliance_check, client_db, result, status, or id. "
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
    ordering_fields = ["compliance_check", "client_db", "result", "status", "id"]


@extend_schema_view(
    list=extend_schema(
        summary="List compliance checks",
        description=(
            "Return a list of all compliance checks. Results default to newest first. "
            "Supports filtering by framework, database and status, and ordering by date, "
            "framework, client_db, status, or id."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve a compliance check",
        description="Return the details of a specific compliance check by ID.",
    ),
    create=extend_schema(
        summary="Submit a compliance check",
        description=(
            "Submit a new compliance check. Pass `client_db`, `framework`, and `schema_name` — "
            "the system resolves the latest uploaded version of that schema automatically. "
            "Saves the record and immediately triggers an asynchronous Celery pipeline to "
            "evaluate compliance assertions. "
            "Track processing progress via the `stream-check-updates` SSE endpoint."
        ),
        request=serializers.ComplianceCheckSerializer,
        responses={
            201: inline_serializer(
                name="ComplianceCheckCreatedResponse",
                fields={
                    "message": rest_framework_serializers.CharField(),
                    "id": rest_framework_serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(
                description="Validation error — invalid IDs or unknown schema name."
            ),
        },
    ),
)
class ComplianceCheckViewSet(viewsets.ModelViewSet):
    queryset = models.ComplianceCheck.objects.all()
    serializer_class = serializers.ComplianceCheckSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_class = ComplianceCheckFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["date", "framework", "client_db", "status", "id"]

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

        # TODO: RETURN INSTEAD AN EMPTY TEMPLATE RESPONSE OF THE SERIALIZER LIKE THE OTHER VIEWSETS
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
        "forwarding events in CloudEvent format until the pipeline reaches a terminal state.\n\n"
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
        200: OpenApiResponse(description="Current inference server status."),
    },
    summary="Get inference server status",
    description=(
        "Return the current state of the llama-server inference server.\n\n"
        "Queries the server's `/health` endpoint directly. "
        'Possible statuses: "not_initialized", "initializing", "initialized", "error".\n\n'
        "Requires authentication."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def model_status(request) -> Response:
    if settings.USE_MOCK_COMPLIANCE_CHECKER:
        return Response(
            {
                "status": "initialized",
                "details": {"disclaimer": "Mock compliance checker is enabled."},
            },
            status=status.HTTP_200_OK,
        )

    return Response(LLMInference().health(), status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter(
            "db_id",
            int,
            location=OpenApiParameter.QUERY,
            required=True,
            description="ID of the ClientDB whose schema history to analyse.",
        ),
        OpenApiParameter(
            "schema_id",
            int,
            location=OpenApiParameter.QUERY,
            required=True,
            description=(
                "ID of the ClientDBSchema that serves as the upper bound. "
                "All schemas for db_id with id ≤ schema_id are included, "
                "ordered chronologically as v1, v2, v3 …"
            ),
        ),
        OpenApiParameter(
            "framework_id",
            int,
            location=OpenApiParameter.QUERY,
            required=False,
            many=True,
            description=(
                "One or more ComplianceFramework IDs to include. "
                "Omit to include all frameworks."
            ),
        ),
    ],
    responses={
        200: OpenApiResponse(
            description=(
                "List of schema versions with per-framework failure counts. "
                'Example: [{"version": "v1", "SOC2": 8, "HIPAA": 14}]'
            )
        ),
        400: OpenApiResponse(description="db_id or schema_id missing or not integers."),
        404: OpenApiResponse(description="schema_id not found under the given db_id."),
    },
    summary="Schema iteration failure counts",
    description=(
        "Returns a chronological series of schema versions for a given database, "
        "each annotated with the number of failing compliance assertions per framework "
        "as of the latest ComplianceCheck recorded for that schema.\n\n"
        "**Version ordering:** all ClientDBSchema records for db_id with id ≤ schema_id, "
        "sorted ascending by id, are labelled v1, v2, v3 …\n\n"
        "**Per-version data:** for each (schema, framework) pair the most recent "
        "ComplianceCheck is used; its assertions where result=False are counted.\n\n"
        "Requires authentication."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def schema_iteration_chart(request):
    raw_db_id = request.query_params.get("db_id")
    raw_schema_id = request.query_params.get("schema_id")

    if not raw_db_id or not raw_schema_id:
        return Response(
            {"detail": "db_id and schema_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        db_id = int(raw_db_id)
        schema_id = int(raw_schema_id)
        framework_ids = [
            int(fid) for fid in request.query_params.getlist("framework_id")
        ]
    except (ValueError, TypeError):
        return Response(
            {"detail": "db_id, schema_id, and framework_id must be integers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    get_object_or_404(models.ClientDBSchema, pk=schema_id, client_db_id=db_id)

    schema_ids = list(
        models.ClientDBSchema.objects.filter(client_db_id=db_id, id__lte=schema_id)
        .order_by("id")
        .values_list("id", flat=True)
    )

    frameworks_qs = models.ComplianceFramework.objects.all()
    if framework_ids:
        frameworks_qs = frameworks_qs.filter(id__in=framework_ids)
    framework_map: dict[int, str] = dict(frameworks_qs.values_list("id", "name"))

    if not framework_map:
        return Response([{"version": f"v{i + 1}"} for i in range(len(schema_ids))])

    # Latest ComplianceCheck id per (schema, framework) pair
    latest_check_map: dict[tuple[int, int], int] = {
        (row["schema_id"], row["framework_id"]): row["latest_id"]
        for row in models.ComplianceCheck.objects.filter(
            schema_id__in=schema_ids,
            framework_id__in=list(framework_map),
        )
        .values("schema_id", "framework_id")
        .annotate(latest_id=Max("id"))
    }

    # Failure counts for each of those checks
    failure_count_map: dict[int, int] = {
        row["compliance_check_id"]: row["count"]
        for row in models.ComplianceAssertion.objects.filter(
            compliance_check_id__in=list(set(latest_check_map.values())),
            result=False,
        )
        .values("compliance_check_id")
        .annotate(count=Count("id"))
    }

    result = []
    for i, sid in enumerate(schema_ids):
        entry: dict[str, int | str] = {"version": f"v{i + 1}"}
        for fw_id, fw_name in framework_map.items():
            check_id = latest_check_map.get((sid, fw_id))
            entry[fw_name] = (
                failure_count_map.get(check_id, 0) if check_id is not None else 0
            )
        result.append(entry)

    return Response(result)
