from django.db import models

class ComplianceFramework(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    version = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("id",)


class ClientDB(models.Model):
    name = models.CharField(max_length=200)
    connection_string = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("id",)


class ClientDBSchema(models.Model):
    client_db = models.ForeignKey(ClientDB, on_delete=models.CASCADE, related_name="schemas")
    schema_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Schema of {self.client_db.name} at {self.created_at}"

    class Meta:
        ordering = ("id",)


class ComplianceAssertion(models.Model):
    compliance_framework = models.ForeignKey(ComplianceFramework, on_delete=models.CASCADE, related_name="assertions")
    client_db = models.ForeignKey(ClientDB, on_delete=models.CASCADE, related_name="compliance_assertions")
    schema = models.ForeignKey(ClientDBSchema, on_delete=models.CASCADE, related_name="compliance_assertions")
    sql_query = models.TextField()
    result = models.BooleanField(null=True)

    def __str__(self):
        return f"Assertion for {self.client_db.name} on {self.compliance_framework.name}"

    class Meta:
        ordering = ("id",)
