from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema_serializer

from .models import (
    ClientDB,
    ClientDBSchema,
    ComplianceAssertion,
    ComplianceCheck,
    ComplianceFramework,
)


# Custom Reusable Comma-Separated Filter
# https://django-filter.readthedocs.io/en/stable/ref/filters.html#django_filters.filters.BaseInFilter
@extend_schema_serializer(many=True)
class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    """Allows comma-separated integers (e.g., ?schema=1,2,3)"""

    pass


class ComplianceAssertionFilter(filters.FilterSet):
    schema = NumberInFilter(field_name="schema__id", lookup_expr="in")
    client_db = NumberInFilter(field_name="client_db__id", lookup_expr="in")
    compliance_framework = NumberInFilter(
        field_name="compliance_framework__id", lookup_expr="in"
    )
    result = filters.BooleanFilter(field_name="result")
    check = NumberInFilter(field_name="compliance_check__id", lookup_expr="in")
    status = filters.MultipleChoiceFilter(
        field_name="status", choices=ComplianceAssertion.Status.choices
    )

    class Meta:
        model = ComplianceAssertion
        fields = [
            "schema",
            "client_db",
            "compliance_framework",
            "result",
            "check",
            "status",
        ]


class ClientDBSchemaFilter(filters.FilterSet):
    client_db = NumberInFilter(field_name="client_db__id", lookup_expr="in")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = ClientDBSchema
        fields = ["client_db", "name"]


class ClientDBFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = ClientDB
        fields = ["name"]


class ComplianceFrameworkFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    description = filters.CharFilter(field_name="description", lookup_expr="icontains")

    class Meta:
        model = ComplianceFramework
        fields = ["name", "description"]


class ComplianceCheckFilter(filters.FilterSet):
    framework = NumberInFilter(field_name="framework__id", lookup_expr="in")
    client_db = NumberInFilter(field_name="client_db__id", lookup_expr="in")
    status = filters.MultipleChoiceFilter(
        field_name="status", choices=ComplianceCheck.Status.choices
    )

    class Meta:
        model = ComplianceCheck
        fields = ["framework", "client_db", "status"]
