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

    framework = serializers.PrimaryKeyRelatedField(
        queryset=ComplianceFramework.objects.all(),
        required=True,
        error_messages={
            "required": "framework_id is required.",
            "does_not_exist": "Invalid framework_id.",
            "incorrect_type": "Invalid framework_id type.",
        },
    )
    schema = serializers.PrimaryKeyRelatedField(
        queryset=ClientDBSchema.objects.all(),
        required=True,
        error_messages={
            "required": "schema_id is required.",
            "does_not_exist": "Invalid schema_id.",
            "incorrect_type": "Invalid schema_id type.",
        },
    )
    client_db = serializers.PrimaryKeyRelatedField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ComplianceCheck
        fields = "__all__"
        read_only_fields = ("date", "client_db", "user")

    def create(self, validated_data):
        schema = validated_data["schema"]
        validated_data["client_db"] = schema.client_db
        return super().create(validated_data)
