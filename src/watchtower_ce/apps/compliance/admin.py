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
    list_display = ("id", "client_db", "created_at")
    list_filter = ("client_db", "created_at")


@admin.register(ComplianceAssertion)
class ComplianceAssertionAdmin(BaseAdmin):
    list_display = (
        "id",
        "compliance_framework",
        "client_db",
        "schema",
        "result",
        "status",
    )
    list_filter = ("result", "status", "compliance_framework", "client_db")
    search_fields = ("sql_query",)


@admin.register(ComplianceCheck)
class ComplianceCheckAdmin(BaseAdmin):
    list_display = ("id", "framework", "client_db", "schema", "user", "date", "status")
    list_filter = ("framework", "client_db", "date", "status")
