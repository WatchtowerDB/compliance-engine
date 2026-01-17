from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from .tasks import (
    schedule_sql_assertion_pipeline,
)


from . import models, serializers


class ComplianceFrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset provides read-only access to compliance framework records.
    """

    queryset: QuerySet = models.ComplianceFramework.objects.all()
    serializer_class: type[Serializer] = serializers.ComplianceFrameworkSerializer


class ClientDBViewSet(viewsets.ModelViewSet):
    """
    This viewset allows full CRUD (Create, Retrieve, Update, Delete) operations
    on client database entries.
    """

    queryset: QuerySet = models.ClientDB.objects.all()
    serializer_class: type[Serializer] = serializers.ClientDBSerializer


class ClientDBSchemaViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ClientDBSchema.objects.all()
    serializer_class: type[Serializer] = serializers.ClientDBSchemaSerializer

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
    serializer_class: type[Serializer] = serializers.ComplianceAssertionSerializer


class ComplianceCheckViewSet(viewsets.ModelViewSet):
    """
    Create and read compliance check records.
    Update and delete operations are disallowed.
    Validation is handled in the serializer.
    """

    queryset: QuerySet = models.ComplianceCheck.objects.all()
    serializer_class: serializers.ComplianceCheckSerializer
    http_method_names: list[str] = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        """
        1. Save the ComplianceCheck instance.
        2. Trigger the Celery async pipeline.
        3. Return a custom response with a message and created ID.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check = serializer.save()

        # Trigger Celery async task
        schedule_sql_assertion_pipeline.delay(
            schema_id=check.schema.id,
            client_db_id=check.client_db.id,
            framework_id=check.framework.id,
        )

        return Response(
            {
                "message": "Compliance check created. Assertions are processing.",
                "id": check.id,
            },
            status=201,
        )
