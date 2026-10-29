from rest_framework import status

from tickets.models import Category, Comment, Ticket

from .helpers import SupportDeskTestCase, make_ticket

LIST_URL = "/api/tickets/"


def detail_url(ticket):
    return f"/api/tickets/{ticket.pk}/"


class TicketCreateTests(SupportDeskTestCase):
    def payload(self, **overrides):
        data = {
            "title": "Cannot log in",
            "description": "The login page keeps loading.",
            "category": self.category.pk,
            "priority": "high",
        }
        return {**data, **overrides}

    def test_customer_creates_ticket(self):
        self.login_as(self.customer)

        response = self.client.post(LIST_URL, self.payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = Ticket.objects.get(pk=response.data["id"])
        self.assertEqual(ticket.created_by, self.customer)
        self.assertEqual(ticket.status, Ticket.Status.OPEN)
        self.assertIsNone(ticket.assigned_to)

    def test_customer_cannot_set_status_when_creating(self):
        self.login_as(self.customer)

        response = self.client.post(LIST_URL, self.payload(status="closed"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_missing_fields_are_rejected(self):
        self.login_as(self.customer)

        response = self.client.post(LIST_URL, {"title": "Only a title"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("description", response.data)
        self.assertIn("category", response.data)

    def test_agent_and_admin_cannot_create_tickets(self):
        for user in (self.agent, self.admin):
            self.login_as(user)
            response = self.client.post(LIST_URL, self.payload())
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_gets_401(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, status.HTTP_401_UNAUTHORIZED)


class TicketVisibilityTests(SupportDeskTestCase):
    def setUp(self):
        super().setUp()
        self.mine = make_ticket(self.customer, self.category, assigned_to=self.agent)
        self.theirs = make_ticket(self.other_customer, self.category, assigned_to=self.other_agent)
        self.unassigned = make_ticket(self.other_customer, self.category)

    def listed_ids(self):
        return {t["id"] for t in self.client.get(LIST_URL).data["results"]}

    def test_customer_sees_only_own_tickets(self):
        self.login_as(self.customer)

        self.assertEqual(self.listed_ids(), {self.mine.pk})

    def test_customer_cannot_open_another_customers_ticket(self):
        self.login_as(self.customer)

        response = self.client.get(detail_url(self.theirs))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_agent_sees_only_assigned_tickets(self):
        self.login_as(self.agent)

        self.assertEqual(self.listed_ids(), {self.mine.pk})
        self.assertEqual(
            self.client.get(detail_url(self.unassigned)).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_admin_sees_all_tickets(self):
        self.login_as(self.admin)

        self.assertEqual(self.listed_ids(), {self.mine.pk, self.theirs.pk, self.unassigned.pk})

    def test_list_uses_a_fixed_number_of_queries(self):
        for _ in range(5):
            make_ticket(self.customer, self.category, assigned_to=self.agent)
        self.login_as(self.admin)

        # One query to count for pagination and one for the page with joined users and category.
        with self.assertNumQueries(2):
            response = self.client.get(LIST_URL)

        self.assertEqual(response.data["count"], 8)


class TicketUpdateTests(SupportDeskTestCase):
    def setUp(self):
        super().setUp()
        self.ticket = make_ticket(self.customer, self.category, assigned_to=self.agent)

    def test_agent_can_change_status_of_assigned_ticket(self):
        self.login_as(self.agent)

        response = self.client.patch(detail_url(self.ticket), {"status": "in_progress"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "in_progress")

    def test_agent_cannot_change_other_fields(self):
        self.login_as(self.agent)

        response = self.client.patch(detail_url(self.ticket), {"title": "Changed"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.ticket.refresh_from_db()
        self.assertNotEqual(self.ticket.title, "Changed")

    def test_agent_cannot_update_ticket_assigned_to_someone_else(self):
        self.login_as(self.other_agent)

        response = self.client.patch(detail_url(self.ticket), {"status": "closed"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_cannot_change_status(self):
        self.login_as(self.customer)

        response = self.client.patch(detail_url(self.ticket), {"status": "closed"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_edit_only_while_ticket_is_open(self):
        self.login_as(self.customer)
        first = self.client.patch(detail_url(self.ticket), {"title": "Printer still broken"})

        self.ticket.status = Ticket.Status.IN_PROGRESS
        self.ticket.save()
        second = self.client.patch(detail_url(self.ticket), {"title": "Another change"})

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_is_not_allowed(self):
        self.login_as(self.admin)

        response = self.client.put(detail_url(self.ticket), {"status": "closed"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_resolved_at_is_set_on_resolve_and_cleared_on_reopen(self):
        self.login_as(self.agent)

        self.client.patch(detail_url(self.ticket), {"status": "resolved"})
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.resolved_at)

        self.client.patch(detail_url(self.ticket), {"status": "open"})
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.resolved_at)

    def test_only_admin_can_delete(self):
        self.login_as(self.customer)
        self.assertEqual(
            self.client.delete(detail_url(self.ticket)).status_code, status.HTTP_403_FORBIDDEN
        )

        self.login_as(self.admin)
        response = self.client.delete(detail_url(self.ticket))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ticket.objects.filter(pk=self.ticket.pk).exists())


class AssignTicketTests(SupportDeskTestCase):
    def setUp(self):
        super().setUp()
        self.ticket = make_ticket(self.customer, self.category)
        self.url = f"/api/tickets/{self.ticket.pk}/assign/"

    def test_admin_assigns_ticket_to_agent(self):
        self.login_as(self.admin)

        response = self.client.post(self.url, {"agent": self.agent.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assigned_to"]["id"], self.agent.pk)

    def test_non_admins_cannot_assign(self):
        for user in (self.customer, self.agent):
            self.login_as(user)
            response = self.client.post(self.url, {"agent": self.agent.pk})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_assign_to_a_customer(self):
        self.login_as(self.admin)

        response = self.client.post(self.url, {"agent": self.other_customer.pk})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.assigned_to)


class CommentTests(SupportDeskTestCase):
    def setUp(self):
        super().setUp()
        self.ticket = make_ticket(self.customer, self.category, assigned_to=self.agent)
        self.url = f"/api/tickets/{self.ticket.pk}/comments/"

    def test_customer_and_agent_can_comment(self):
        for user in (self.customer, self.agent):
            self.login_as(user)
            response = self.client.post(self.url, {"message": f"Hello from {user.username}"})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["author"]["id"], user.pk)

        self.assertEqual(self.client.get(self.url).data[1]["message"], "Hello from agent")

    def test_cannot_comment_on_ticket_you_cannot_see(self):
        self.login_as(self.other_customer)

        response = self.client.post(self.url, {"message": "Let me in"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Comment.objects.exists())

    def test_empty_comment_is_rejected(self):
        self.login_as(self.customer)

        response = self.client.post(self.url, {"message": ""})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ticket_detail_includes_comments(self):
        Comment.objects.create(ticket=self.ticket, author=self.agent, message="On it")
        self.login_as(self.customer)

        response = self.client.get(detail_url(self.ticket))

        self.assertEqual(response.data["comment_count"], 1)
        self.assertEqual(response.data["comments"][0]["message"], "On it")


class CategoryTests(SupportDeskTestCase):
    def test_everyone_can_list_but_only_admin_can_create(self):
        self.login_as(self.customer)
        self.assertEqual(len(self.client.get("/api/categories/").data), 1)
        denied = self.client.post("/api/categories/", {"name": "Billing"})

        self.login_as(self.admin)
        created = self.client.post("/api/categories/", {"name": "Billing"})

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

    def test_category_with_tickets_cannot_be_deleted(self):
        make_ticket(self.customer, self.category)
        self.login_as(self.admin)

        response = self.client.delete(f"/api/categories/{self.category.pk}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
