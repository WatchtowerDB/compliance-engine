from django.db import models, transaction
from django.db.models import Max
from rest_framework import serializers

from .models import (
    ClientDB,
    ClientDBSchema,
    ComplianceAssertion,
    ComplianceCheck,
    ComplianceFramework,
)


class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model: type[models.Model] = ComplianceFramework
        fields: str = "__all__"


class ClientDBSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = ClientDB
        fields = "__all__"


class ClientDBSchemaSerializer(serializers.ModelSerializer):
    internal_version = serializers.IntegerField(read_only=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = ClientDBSchema
        fields = "__all__"
        read_only_fields = ("internal_version",)

    def create(self, validated_data):
        client_db = validated_data["client_db"]
        name = validated_data["name"]

        with transaction.atomic():
            max_version = (
                ClientDBSchema.objects.select_for_update()
                .filter(client_db=client_db, name=name)
                .aggregate(Max("internal_version"))["internal_version__max"]
            )
            validated_data["internal_version"] = (max_version or 0) + 1
            return super().create(validated_data)


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
    name = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")

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
        sql_file = validated_data["sql_file"]
        client_db = validated_data["client_db"]
        name = validated_data["name"]
        description = validated_data.get("description", "")
        sql_content = sql_file.read().decode("utf-8")

        with transaction.atomic():
            max_version = (
                ClientDBSchema.objects.select_for_update()
                .filter(client_db=client_db, name=name)
                .aggregate(Max("internal_version"))["internal_version__max"]
            )
            internal_version = (max_version or 0) + 1

            schema = ClientDBSchema.objects.create(
                client_db=client_db,
                name=name,
                description=description or None,
                sql_definition=sql_content,
                internal_version=internal_version,
            )

        return schema


class ComplianceAssertionSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = ComplianceAssertion
        fields = "__all__"


class ComplianceCheckSchemaSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = ClientDBSchema
        fields = ("id", "name", "internal_version")


class ComplianceCheckSerializer(serializers.ModelSerializer):
    framework = serializers.PrimaryKeyRelatedField(
        queryset=ComplianceFramework.objects.all(),
        required=True,
        help_text="ID of the compliance framework to evaluate against (e.g. SOC2, HIPAA).",
        error_messages={
            "required": "framework is required.",
            "does_not_exist": "Invalid framework ID.",
            "incorrect_type": "Invalid framework type.",
        },
    )
    client_db = serializers.PrimaryKeyRelatedField(
        queryset=ClientDB.objects.all(),
        required=True,
        help_text="ID of the client database to check.",
        error_messages={
            "required": "client_db is required.",
            "does_not_exist": "Invalid client_db ID.",
            "incorrect_type": "Invalid client_db type.",
        },
    )
    schema_name = serializers.CharField(
        write_only=True,
        required=True,
        help_text=(
            "Name of the schema group to check. "
            "The system automatically resolves to the latest uploaded version."
        ),
    )
    schema = ComplianceCheckSchemaSerializer(
        read_only=True,
        help_text=(
            "Details of the exact schema version that was resolved and used for this check."
        ),
    )
    # Will change later to its own serializer to match the schema one
    client_db_name = serializers.CharField(source="client_db.name", read_only=True)
    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        help_text="ID of the user who submitted this check.",
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = ComplianceCheck
        fields = (
            "id",
            "framework",
            "client_db",
            "client_db_name",
            "schema",
            "schema_name",
            "user",
            "date",
            "status",
        )
        read_only_fields = ("date", "schema", "user", "status")

    def validate(self, attrs):
        client_db = attrs["client_db"]
        schema_name = attrs.pop("schema_name")

        schema = (
            ClientDBSchema.objects.filter(client_db=client_db, name=schema_name)
            .order_by("-internal_version")
            .first()
        )
        if schema is None:
            raise serializers.ValidationError(
                {
                    "schema_name": f"No schema named '{schema_name}' exists for the given client_db."
                }
            )

        attrs["schema"] = schema
        return attrs
