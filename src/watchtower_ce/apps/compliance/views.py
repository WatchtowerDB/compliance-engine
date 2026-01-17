from django.db.models import QuerySet
from rest_framework import status, viewsets
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Schema uploaded successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

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
    This viewset allows creating and reading compliance check records.
    Update and delete operations are explicitly disallowed.
    """

    queryset: QuerySet = models.ComplianceCheck.objects.all()
    serializer_class: type[Serializer] = serializers.ComplianceCheckSerializer
    http_method_names: list[str] = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        framework_id = request.data.get("framework_id")
        schema_id = request.data.get("schema_id")

        if not framework_id or not schema_id:
            return Response(
                {"detail": "framework_id and schema_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            framework = models.ComplianceFramework.objects.get(id=framework_id)
            schema = models.ClientDBSchema.objects.get(id=schema_id)
        except (
            models.ComplianceFramework.DoesNotExist,
            models.ClientDBSchema.DoesNotExist,
        ):
            return Response(
                {"detail": "Invalid framework_id or schema_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        check = models.ComplianceCheck.objects.create(
            framework=framework,
            client_db=schema.client_db,
            schema=schema,
        )

        # Trigger Celery async pipeline
        schedule_sql_assertion_pipeline.delay(
            schema_id=schema.id,
            client_db_id=schema.client_db.id,
            framework_id=framework.id,
        )

        return Response(
            {
                "message": "Compliance check created. Assertions are processing.",
                "id": check.id,
            },
            status=status.HTTP_201_CREATED,
        )
