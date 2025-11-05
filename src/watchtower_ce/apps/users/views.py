from django.contrib.auth.models import User
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.serializers import Serializer

from . import serializers


class UserViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = User.objects.all()
    serializer_class: type[Serializer] = serializers.UserSerializer
