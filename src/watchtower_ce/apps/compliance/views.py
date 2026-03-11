from django.db.models import QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .tasks import schedule_sql_assertion_pipeline
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

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Update not allowed."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Partial update not allowed."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Delete not allowed."}, status=405)

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="upload-schema",
    )
    def upload_schema(self, request):
        """
        Upload a .sql file to create a new ClientDBSchema.

        All validation is handled by ClientDBSchemaUploadSerializer.

        Expected form data:
        - sql_file: The .sql file to upload (required)
        - client_db: ID of the ClientDB (required)

        """
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


class ComplianceAssertionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset provides read-only access to compliance assertion records.
    """

    queryset: QuerySet = models.ComplianceAssertion.objects.select_related(
        "schema", "client_db", "compliance_framework"
    )
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
        )

        return Response(
            {
                "message": "Compliance check created. Assertions are processing.",
                "id": check.id,
            },
            status=201,
        )
