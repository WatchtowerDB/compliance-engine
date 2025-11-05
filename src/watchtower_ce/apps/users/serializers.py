from typing import Iterable

from django.contrib.auth.models import User
from django.db.models import Model
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model: type[Model] = User
        fields: Iterable[str] = (
            "email",
            "username",
            "first_name",
            "last_name",
            "groups",
        )
