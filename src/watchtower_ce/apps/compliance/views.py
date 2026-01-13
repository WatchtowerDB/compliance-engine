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
    """
    This viewset allows listing, creating, and retrieving schema records.
    Update, partial update, and delete operations are explicitly disallowed.
    """

    queryset: QuerySet = models.ClientDBSchema.objects.all()
    serializer_class: type[Serializer] = serializers.ClientDBSchemaSerializer

    def create(self, request, *args, **kwargs):
        serializers = self.get_serializer(data=request.data)
        serializers.is_valid(raise_exception=True)
        schema_object = serializers.save()
        # Trigger async compliance pipelines
        schedule_sql_assertion_pipeline.delay(
            schema_id=schema_object.id, client_db_id=schema_object.client_db.id
        )

        headers = self.get_success_headers(serializers.data)
        return Response(
            {
                "message": "Schema uploaded successfully. Assertions have been auto-generated",
                "data": serializers.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        """Disallow update operation for client database schemas."""
        return Response(
            {"detail": "Update not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """Disallow partial update operation for client database schemas."""
        return Response(
            {"detail": "Partial update not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Disallow delete operation for client database schemas."""
        return Response(
            {"detail": "Delete not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


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
