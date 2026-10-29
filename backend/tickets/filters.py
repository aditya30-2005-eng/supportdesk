import django_filters

from .models import Ticket


class TicketFilter(django_filters.FilterSet):
    unassigned = django_filters.BooleanFilter(field_name="assigned_to", lookup_expr="isnull")
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Ticket
        fields = ["status", "priority", "category", "assigned_to"]
