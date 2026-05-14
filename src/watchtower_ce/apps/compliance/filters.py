from django_filters import rest_framework as filters
from .models import ComplianceAssertion, ClientDBSchema, ClientDB, ComplianceFramework


class ComplianceAssertionFilter(filters.FilterSet):
    schema = filters.NumberFilter(field_name="schema__id")
    client_db = filters.NumberFilter(field_name="client_db__id")
    compliance_framework = filters.NumberFilter(field_name="compliance_framework__id")
    result = filters.BooleanFilter(field_name="result")
    check = filters.NumberFilter(field_name="compliance_check__id")

    class Meta:
        model = ComplianceAssertion
        fields = ["schema", "client_db", "compliance_framework", "result", "check"]


class ClientDBSchemaFilter(filters.FilterSet):
    client_db = filters.NumberFilter(field_name="client_db__id")

    class Meta:
        model = ClientDBSchema
        fields = ["client_db"]


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
