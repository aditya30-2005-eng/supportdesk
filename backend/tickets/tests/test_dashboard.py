from datetime import timedelta

from django.utils import timezone

from tickets.models import Ticket

from .helpers import SupportDeskTestCase, make_ticket

URL = "/api/dashboard/stats/"


class DashboardStatsTests(SupportDeskTestCase):
    def setUp(self):
        super().setUp()
        start = timezone.now() - timedelta(days=2)
        resolved_in_2h = make_ticket(
            self.customer, self.category, status="resolved", assigned_to=self.agent
        )
        closed_in_4h = make_ticket(
            self.customer, self.category, status="closed", priority="high", assigned_to=self.agent
        )
        make_ticket(self.customer, self.category, status="in_progress", assigned_to=self.agent)
        make_ticket(self.other_customer, self.category, priority="urgent")

        # Fix the timestamps so the average is known: (2h + 4h) / 2 = 3h.
        Ticket.objects.filter(pk=resolved_in_2h.pk).update(
            created_at=start, resolved_at=start + timedelta(hours=2)
        )
        Ticket.objects.filter(pk=closed_in_4h.pk).update(
            created_at=start, resolved_at=start + timedelta(hours=4)
        )

    def test_admin_gets_counts_and_average_resolution_time(self):
        self.login_as(self.admin)

        data = self.client.get(URL).data

        self.assertEqual(data["total"], 4)
        self.assertEqual(data["unassigned"], 1)
        self.assertEqual(
            data["by_status"], {"open": 1, "in_progress": 1, "resolved": 1, "closed": 1}
        )
        self.assertEqual(data["by_priority"], {"low": 0, "medium": 2, "high": 1, "urgent": 1})
        self.assertEqual(data["average_resolution_hours"], 3.0)

    def test_agent_workload_counts(self):
        self.login_as(self.admin)

        agents = {a["username"]: a for a in self.client.get(URL).data["agents"]}

        self.assertEqual(agents["agent"]["open_tickets"], 1)
        self.assertEqual(agents["agent"]["done_tickets"], 2)
        self.assertEqual(agents["agent2"]["open_tickets"], 0)

    def test_average_is_null_when_nothing_is_resolved(self):
        Ticket.objects.filter(resolved_at__isnull=False).delete()
        self.login_as(self.admin)

        self.assertIsNone(self.client.get(URL).data["average_resolution_hours"])

    def test_only_admin_can_see_stats(self):
        for user in (self.customer, self.agent):
            self.login_as(user)
            self.assertEqual(self.client.get(URL).status_code, 403)
