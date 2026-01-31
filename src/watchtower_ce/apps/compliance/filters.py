from django_filters import rest_framework as filters
from .models import ComplianceAssertion, ClientDBSchema


class ComplianceAssertionFilter(filters.FilterSet):
    schema = filters.NumberFilter(field_name="schema__id")
    client_db = filters.NumberFilter(field_name="client_db__id")
    compilance_framework = filters.NumberFilter(field_name="compliance_framework__id")
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
