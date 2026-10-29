from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tickets.models import Category, Ticket

User = get_user_model()

PASSWORD = "Str0ng-pass-123"


def make_user(username, role=User.Role.CUSTOMER):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=PASSWORD, role=role
    )


def make_ticket(created_by, category, **fields):
    fields.setdefault("title", "Printer is not working")
    fields.setdefault("description", "It shows a paper jam error.")
    return Ticket.objects.create(created_by=created_by, category=category, **fields)


class SupportDeskTestCase(APITestCase):
    """Creates one user of each role and a category for every test."""

    def setUp(self):
        self.admin = make_user("admin", User.Role.ADMIN)
        self.agent = make_user("agent", User.Role.AGENT)
        self.other_agent = make_user("agent2", User.Role.AGENT)
        self.customer = make_user("customer")
        self.other_customer = make_user("customer2")
        self.category = Category.objects.create(name="Technical")

    def login_as(self, user):
        self.client.force_authenticate(user)
