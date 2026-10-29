from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Prefetch,
    ProtectedError,
    Q,
    Value,
    When,
)
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrReadOnly, IsAdminRole, IsCustomerRole

from .filters import TicketFilter
from .models import Category, Comment, Ticket
from .serializers import (
    AssignTicketSerializer,
    CategorySerializer,
    CommentSerializer,
    DashboardStatsSerializer,
    TicketDetailSerializer,
    TicketSerializer,
)

User = get_user_model()

PRIORITY_RANK = Case(
    When(priority=Ticket.Priority.LOW, then=Value(1)),
    When(priority=Ticket.Priority.MEDIUM, then=Value(2)),
    When(priority=Ticket.Priority.HIGH, then=Value(3)),
    When(priority=Ticket.Priority.URGENT, then=Value(4)),
    output_field=IntegerField(),
)


def tickets_visible_to(user):
    """The single place that decides which tickets a user may see."""
    tickets = Ticket.objects.all()
    if user.is_admin:
        return tickets
    if user.is_agent:
        return tickets.filter(assigned_to=user)
    return tickets.filter(created_by=user)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    search_fields = ["name"]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                "This category still has tickets, so it cannot be deleted."
            ) from error


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.none()
    filterset_class = TicketFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority_rank", "status"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()
        queryset = (
            tickets_visible_to(self.request.user)
            .select_related("category", "created_by", "assigned_to")
            .annotate(comment_count=Count("comments"), priority_rank=PRIORITY_RANK)
        )
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                Prefetch("comments", queryset=Comment.objects.select_related("author"))
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TicketDetailSerializer
        if self.action == "assign":
            return AssignTicketSerializer
        if self.action == "comments":
            return CommentSerializer
        return TicketSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsCustomerRole()]
        if self.action in ("destroy", "assign"):
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(request=AssignTicketSerializer, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket.assigned_to = serializer.validated_data["agent"]
        ticket.save()
        return Response(TicketSerializer(ticket, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "GET":
            comments = ticket.comments.select_related("author")
            return Response(self.get_serializer(comments, many=True).data)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(ticket=ticket, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DashboardStatsView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(responses=DashboardStatsSerializer)
    def get(self, request):
        tickets = Ticket.objects.all()
        totals = tickets.aggregate(
            total=Count("id"),
            unassigned=Count("id", filter=Q(assigned_to__isnull=True)),
            average_resolution=Avg(
                ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField()),
                filter=Q(resolved_at__isnull=False),
            ),
        )
        return Response(
            {
                "total": totals["total"],
                "unassigned": totals["unassigned"],
                "by_status": self._count_by(tickets, "status", Ticket.Status),
                "by_priority": self._count_by(tickets, "priority", Ticket.Priority),
                "average_resolution_hours": self._to_hours(totals["average_resolution"]),
                "agents": self._agent_workload(),
            }
        )

    @staticmethod
    def _count_by(tickets, field, choices):
        counts = {value: 0 for value in choices.values}
        for row in tickets.values(field).annotate(count=Count("id")).order_by():
            counts[row[field]] = row["count"]
        return counts

    @staticmethod
    def _to_hours(duration):
        if duration is None:
            return None
        return round(duration / timedelta(hours=1), 1)

    @staticmethod
    def _agent_workload():
        working_on = Q(assigned_tickets__status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS])
        done = Q(assigned_tickets__status__in=Ticket.DONE_STATUSES)
        agents = (
            User.objects.filter(role=User.Role.AGENT, is_active=True)
            .annotate(
                open_tickets=Count("assigned_tickets", filter=working_on),
                done_tickets=Count("assigned_tickets", filter=done),
            )
            .order_by("username")
        )
        return [
            {
                "id": agent.id,
                "username": agent.username,
                "full_name": agent.get_full_name() or agent.username,
                "open_tickets": agent.open_tickets,
                "done_tickets": agent.done_tickets,
            }
            for agent in agents
        ]
