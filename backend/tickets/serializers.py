from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Category, Comment, Ticket

User = get_user_model()

CREATE_FIELDS = {"title", "description", "category", "priority"}

# Fields each role is allowed to change with PATCH /tickets/<id>/.
EDITABLE_FIELDS_BY_ROLE = {
    User.Role.CUSTOMER: {"title", "description", "category", "priority"},
    User.Role.AGENT: {"status"},
    User.Role.ADMIN: {"status", "priority", "category"},
}


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "message", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    comment_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_name",
            "priority",
            "status",
            "created_by",
            "assigned_to",
            "comment_count",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "resolved_at"]

    def validate(self, attrs):
        sent_fields = set(self.initial_data) & set(self.fields)
        allowed = self._allowed_fields()
        blocked = sorted(sent_fields - allowed)
        if blocked:
            raise serializers.ValidationError(
                {field: "You are not allowed to set this field." for field in blocked}
            )
        if self._is_customer_editing_closed_ticket():
            raise serializers.ValidationError("You can only edit a ticket while it is open.")
        return attrs

    def _allowed_fields(self):
        if self.instance is None:
            return CREATE_FIELDS
        return EDITABLE_FIELDS_BY_ROLE.get(self.context["request"].user.role, set())

    def _is_customer_editing_closed_ticket(self):
        user = self.context["request"].user
        return (
            self.instance is not None
            and user.is_customer
            and self.instance.status != Ticket.Status.OPEN
        )


class TicketDetailSerializer(TicketSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ["comments"]


class AssignTicketSerializer(serializers.Serializer):
    agent = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.AGENT, is_active=True),
        error_messages={"does_not_exist": "Pick an active agent."},
    )


class AgentWorkloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    open_tickets = serializers.IntegerField()
    done_tickets = serializers.IntegerField()


class DashboardStatsSerializer(serializers.Serializer):
    """Describes the dashboard response for the API docs."""

    total = serializers.IntegerField()
    unassigned = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_priority = serializers.DictField(child=serializers.IntegerField())
    average_resolution_hours = serializers.FloatField(allow_null=True)
    agents = AgentWorkloadSerializer(many=True)
