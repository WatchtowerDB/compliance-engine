from django_filters import rest_framework as filters
from .models import ComplianceAssertion


class ComplianceAssertionFilter(filters.FilterSet):
    schema = filters.NumberFilter(field_name="schema__id")

    class Meta:
        model = ComplianceAssertion
        fields = ["schema"]
