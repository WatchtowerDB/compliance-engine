from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.serializers import Serializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from . import models, serializers



# ComplianceFramework (Read-only)

class ComplianceFrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet = models.ComplianceFramework.objects.all()
    serializer_class: type[Serializer] = serializers.ComplianceFrameworkSerializer
    permission_classes = [IsAuthenticated]



# ClientDB (Full CRUD)

class ClientDBViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ClientDB.objects.all()
    serializer_class: type[Serializer] = serializers.ClientDBSerializer
    



# ClientDBSchema (List, Create, Retrieve only)

class ClientDBSchemaViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = models.ClientDBSchema.objects.all()
    serializer_class: type[Serializer] = serializers.ClientDBSchemaSerializer
   

    # Limit actions to list, create, retrieve
    def get_queryset(self):
        return super().get_queryset()

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Update not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Partial update not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Delete not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )



# ComplianceAssertion (Read-only)

class ComplianceAssertionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet = models.ComplianceAssertion.objects.all()
    serializer_class: type[Serializer] = serializers.ComplianceAssertionSerializer
    
