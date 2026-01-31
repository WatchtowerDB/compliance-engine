import json
import redis
import datetime
from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .tasks import (
    schedule_sql_assertion_pipeline,
    initialize_model_task,
)

from . import models, serializers
from .filters import ComplianceAssertionFilter, ClientDBSchemaFilter


class ComplianceFrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset provides read-only access to compliance framework records.
    """

    queryset: QuerySet = models.ComplianceFramework.objects.all()
    serializer_class = serializers.ComplianceFrameworkSerializer


class ClientDBViewSet(viewsets.ModelViewSet):
    """
    This viewset allows full CRUD (Create, Retrieve, Update, Delete) operations
    on client database entries.
    """

    queryset: QuerySet = models.ClientDB.objects.all()
    serializer_class = serializers.ClientDBSerializer


class ClientDBSchemaViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ClientDBSchema.objects.all()
    serializer_class = serializers.ClientDBSchemaSerializer
    filterset_class = ClientDBSchemaFilter

    # Disallow updates/deletes
    def update(self, request, *args, **kwargs):
        return Response({"detail": "Update not allowed."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Partial update not allowed."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Delete not allowed."}, status=405)


class ComplianceAssertionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset provides read-only access to compliance assertion records.
    """

    queryset: QuerySet = models.ComplianceAssertion.objects.all()
    serializer_class = serializers.ComplianceAssertionSerializer
    filterset_class = ComplianceAssertionFilter


class ComplianceCheckViewSet(viewsets.ModelViewSet):
    """
    Create and read compliance check records.
    Update and delete operations are disallowed.
    Validation is handled in the serializer.
    """

    queryset: QuerySet = models.ComplianceCheck.objects.all()
    serializer_class = serializers.ComplianceCheckSerializer
    http_method_names: list[str] = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        """
        1. Save the ComplianceCheck instance.
        2. Trigger the Celery async pipeline.
        3. Return a custom response with a message and created ID.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check = serializer.save(user=request.user)

        # Trigger Celery async task
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stream_check_updates(request, check_id):
    """
    SSE Endpoint: Streams updates for a specific ComplianceCheck ID.

    Workflow:
    1. Validation: Verifies that the ComplianceCheck exists.
    2. Completion Check: Checks if the pipeline has already finished processing (i.e., failed assertions exist and all have recommendations).
       If finished, immediately yields a completion event.
    3. Connection: Establishes a connection to Redis and subscribes to the check-specific channel.
    4. Streaming:
       - Sends an initial 'connected' event.
       - Listens for messages on the Redis channel.
       - Decodes CloudEvents (bytes to string) and streams them to the client.
    """
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stream_model_init(request):
    """
    SSE Endpoint: Initialize the model via Celery and stream the status.

    Process:
    1. Connection: Connects to Redis and subscribes to the global updates channel.
    2. Initialization: Sends a 'connected' event and triggers the asynchronous model initialization task.
    3. Streaming: Listens for status updates from Redis.
       - Decodes and yields messages.
       - Closes the stream upon receiving terminal statuses (initialized, already_initialized, error).
    """

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
                        status = payload.get("status")

                        yield f"data: {data}\n\n"

                        if status in ["initialized", "already_initialized", "error"]:
                            break
                    except json.JSONDecodeError:
                        yield f"data: {data}\n\n"
        finally:
            pubsub.unsubscribe(channel_name)
            r.close()

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
