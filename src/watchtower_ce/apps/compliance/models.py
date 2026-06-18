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
    name = models.CharField(max_length=200, default="")
    description = models.TextField(null=True, blank=True)
    sql_definition = models.TextField(null=True, blank=True)
    internal_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["client_db", "name", "internal_version"]
        ordering: tuple[str, ...] = ("id",)


class ComplianceAssertion(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        EXECUTING = "EXECUTING", "Executing"
        ANALYZING = "ANALYZING", "Analyzing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    compliance_framework: models.ForeignKey = models.ForeignKey(
        "ComplianceFramework", on_delete=models.CASCADE, related_name="assertions"
    )
    client_db: models.ForeignKey = models.ForeignKey(
        "ClientDB", on_delete=models.CASCADE, related_name="compliance_assertions"
    )
    schema: models.ForeignKey = models.ForeignKey(
        "ClientDBSchema", on_delete=models.CASCADE, related_name="compliance_assertions"
    )
    compliance_check: models.ForeignKey = models.ForeignKey(
        "ComplianceCheck", on_delete=models.CASCADE, related_name="assertions"
    )
    sql_query: models.TextField = models.TextField()
    query_output: models.TextField = models.TextField(null=True, blank=True)
    result: models.BooleanField = models.BooleanField(null=True)
    recommendation: models.TextField = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Human-readable recommendation generated asynchronously by celery "
            "tasks; may be null until background processing completes."
        ),
    )
    status: models.CharField = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return (
            f"Assertion for {self.client_db.name} on {self.compliance_framework.name}"
        )

    class Meta:
        ordering: tuple[str, ...] = ("id",)


class ComplianceCheck(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        GENERATING = "GENERATING", "Generating Assertions"
        EXECUTING = "EXECUTING", "Executing Assertions"
        ANALYZING = "ANALYZING", "Analyzing Failures"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

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
    status: models.CharField = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return (
            f"Check for {self.client_db.name} on {self.framework.name} at {self.date}"
        )

    class Meta:
        ordering: tuple[str, ...] = ("id",)
