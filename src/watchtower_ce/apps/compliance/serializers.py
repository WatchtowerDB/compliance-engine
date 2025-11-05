from django.db import models
from rest_framework import serializers

from .models import ComplianceFramework


class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model: type[models.Model] = ComplianceFramework
        fields: str = "__all__"
