from django.contrib import admin

from .models import (
    ClientDB,
    ClientDBSchema,
    ComplianceAssertion,
    ComplianceCheck,
    ComplianceFramework,
)


class BaseAdmin(admin.ModelAdmin):
    """Base admin with default ordering by 'id'."""

    ordering = ("id",)
    list_display_links = ("id",)


@admin.register(ComplianceFramework)
class ComplianceFrameworkAdmin(BaseAdmin):
    list_display = ("id", "name", "version")
    search_fields = ("name", "version")


@admin.register(ClientDB)
class ClientDBAdmin(BaseAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(ClientDBSchema)
class ClientDBSchemaAdmin(BaseAdmin):
    list_display = (
        "id",
        "client_db",
        "name",
        "description",
        "created_at",
        "internal_version",
    )
    list_filter = ("client_db", "name", "created_at", "internal_version")


@admin.register(ComplianceAssertion)
class ComplianceAssertionAdmin(BaseAdmin):
    list_display = ("id", "compliance_framework", "client_db", "schema", "result")
    list_filter = ("result", "compliance_framework", "client_db")
    search_fields = ("sql_query",)


@admin.register(ComplianceCheck)
class ComplianceCheckAdmin(BaseAdmin):
    list_display = ("id", "framework", "client_db", "schema", "user", "date")
    list_filter = ("framework", "client_db", "date")
