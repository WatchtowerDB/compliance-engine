from django.conf import settings
from django.db import models


class ComplianceFramework(models.Model):
    name: models.CharField = models.CharField(max_length=200)
    description: models.TextField = models.TextField()
    version: models.CharField = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering: tuple[str, ...] = ("id",)


class ClientDB(models.Model):
    name: models.CharField = models.CharField(max_length=200)
    connection_string: models.TextField = models.TextField()

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering: tuple[str, ...] = ("id",)


class ClientDBSchema(models.Model):
    client_db: models.ForeignKey = models.ForeignKey(
        "ClientDB", on_delete=models.CASCADE, related_name="schemas"
    )
    schema_json: models.JSONField = models.JSONField()
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Schema of {self.client_db.name} at {self.created_at}"

    class Meta:
        ordering: tuple[str, ...] = ("id",)


class ComplianceAssertion(models.Model):
    compliance_framework: models.ForeignKey = models.ForeignKey(
        "ComplianceFramework", on_delete=models.CASCADE, related_name="assertions"
    )
    client_db: models.ForeignKey = models.ForeignKey(
        "ClientDB", on_delete=models.CASCADE, related_name="compliance_assertions"
    )
    schema: models.ForeignKey = models.ForeignKey(
        "ClientDBSchema", on_delete=models.CASCADE, related_name="compliance_assertions"
    )
    sql_query: models.TextField = models.TextField()
    result: models.BooleanField = models.BooleanField(null=True)

    def __str__(self) -> str:
        return f"Assertion for {self.client_db.name} on {self.compliance_framework.name}"

    class Meta:
        ordering: tuple[str, ...] = ("id",)


class ComplianceCheck(models.Model):
    framework: models.ForeignKey = models.ForeignKey(
        "ComplianceFramework", on_delete=models.CASCADE, related_name="checks"
    )
    client_db: models.ForeignKey = models.ForeignKey(
        "ClientDB", on_delete=models.CASCADE, related_name="checks"
    )
    schema: models.ForeignKey = models.ForeignKey(
        "ClientDBSchema", on_delete=models.CASCADE, related_name="checks"
    )
    date: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="compliance_checks",
    )

    def __str__(self) -> str:
        return f"Check for {self.client_db.name} on {self.framework.name} at {self.date}"

    class Meta:
        ordering: tuple[str, ...] = ("id",)
