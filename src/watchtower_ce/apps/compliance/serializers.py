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


class ClientDBWithFrameworksSerializer(serializers.ModelSerializer):
    frameworks = ComplianceFrameworkSerializer(many=True, read_only=True)

    class Meta:
        model = ClientDB
        fields = ["id", "name", "connection_string", "frameworks"]


class ClientDBSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDBSchema
        fields = "__all__"


class ClientDBSchemaUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading a .sql file to create a ClientDBSchema.
    Handles validation of the file and required fields.
    """

    sql_file = serializers.FileField(
        required=True,
        error_messages={
            "required": "sql_file is required.",
            "invalid": "Invalid file.",
            "empty": "File cannot be empty.",
        },
    )
    client_db = serializers.PrimaryKeyRelatedField(
        queryset=ClientDB.objects.all(),
        required=True,
        error_messages={
            "required": "client_db is required.",
            "does_not_exist": "Invalid client_db ID.",
            "incorrect_type": "Invalid client_db type.",
        },
    )

    def validate_sql_file(self, value):
        """
        Validate that the uploaded file:
        1. Has a .sql extension
        2. Is a valid UTF-8 encoded text file
        3. Is not empty
        """

        if not value.name.endswith(".sql"):
            raise serializers.ValidationError("File must have a .sql extension.")

        if value.size == 0:
            raise serializers.ValidationError("File cannot be empty.")

        try:
            content = value.read().decode("utf-8")

            value.seek(0)

            if not content.strip():
                raise serializers.ValidationError(
                    "File cannot contain only whitespace."
                )
        except UnicodeDecodeError:
            raise serializers.ValidationError(
                "File must be a valid UTF-8 encoded text file."
            )
        except Exception as e:
            raise serializers.ValidationError(f"Error reading file: {str(e)}")

        return value

    def create(self, validated_data):
        """
        Create a ClientDBSchema instance from the validated data.
        """
        sql_file = validated_data["sql_file"]
        client_db = validated_data["client_db"]

        sql_content = sql_file.read().decode("utf-8")

        schema = ClientDBSchema.objects.create(
            client_db=client_db,
            sql_definition=sql_content,
        )

        return schema


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
