from django.contrib.auth.models import User
from django.db.models import QuerySet
from rest_framework import viewsets


class UserViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = User.objects.all()
