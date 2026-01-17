from django.db import models
from rest_framework import serializers

from .models import (
    ClientDB,
    ComplianceAssertion,
    ClientDBSchema,
    ComplianceFramework,
    ComplianceCheck,
)


class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model: type[models.Model] = ComplianceFramework
        fields: str = "__all__"


class ClientDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDB
        fields = "__all__"


class ClientDBSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDBSchema
        fields = "__all__"


class ComplianceAssertionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAssertion
        fields = "__all__"


class ComplianceCheckSerializer(serializers.ModelSerializer):
    """
    Serializer for ComplianceCheck model.
    Handles validation of foreign keys (framework and schema) automatically.
    The client_db field is read-only and is set automatically from the schema.
    """

    # Validate that framework is a valid foreign key
    framework = serializers.PrimaryKeyRelatedField(
        queryset=ComplianceFramework.objects.all()
    )
    # Validate that schema is a valid foreign key
    schema = serializers.PrimaryKeyRelatedField(queryset=ClientDBSchema.objects.all())

    class Meta:
        model = ComplianceCheck
        fields = "__all__"
        read_only_fields = ("date", "client_db")

    def create(self, validated_data):
        """
        Override create method to automatically assign client_db from the schema.
        Ensures users do not provide client_db manually.
        """
        schema = validated_data["schema"]
        validated_data["client_db"] = schema.client_db
        return super().create(validated_data)
