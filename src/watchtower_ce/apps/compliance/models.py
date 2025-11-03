from django.db import models


class ComplianceFramework(models.Model):
    name: models.CharField = models.CharField(max_length=200)
    description: models.TextField = models.TextField()
    version: models.CharField = models.CharField(max_length=50)

    def __str__(self) -> str:
        return str(self.name)


class ComplianceAssertion(models.Model):
    pass
