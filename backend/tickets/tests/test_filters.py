from tickets.models import Category

from .helpers import SupportDeskTestCase, make_ticket

LIST_URL = "/api/tickets/"


class TicketFilterTests(SupportDeskTestCase):
    def setUp(self):
        super().setUp()
        billing = Category.objects.create(name="Billing")
        self.refund = make_ticket(
            self.customer,
            billing,
            title="Refund not received",
            description="I cancelled my plan last week.",
            priority="high",
        )
        self.crash = make_ticket(
            self.customer,
            self.category,
            title="App crashes",
            description="It closes right after opening, no refund needed.",
            priority="urgent",
            status="in_progress",
            assigned_to=self.agent,
        )
        self.question = make_ticket(
            self.customer,
            self.category,
            title="Question about reports",
            priority="low",
            status="resolved",
            assigned_to=self.agent,
        )
        self.billing = billing
        self.login_as(self.admin)

    def ids(self, **params):
        response = self.client.get(LIST_URL, params)
        return [t["id"] for t in response.data["results"]]

    def test_filter_by_status(self):
        self.assertEqual(self.ids(status="in_progress"), [self.crash.pk])

    def test_filter_by_priority_and_category(self):
        self.assertEqual(self.ids(priority="high"), [self.refund.pk])
        self.assertEqual(self.ids(category=self.billing.pk), [self.refund.pk])
        self.assertEqual(self.ids(category=self.category.pk, priority="high"), [])

    def test_filter_unassigned(self):
        self.assertEqual(self.ids(unassigned="true"), [self.refund.pk])

    def test_search_matches_title_and_description(self):
        self.assertEqual(set(self.ids(search="refund")), {self.refund.pk, self.crash.pk})
        self.assertEqual(self.ids(search="reports"), [self.question.pk])

    def test_ordering_by_priority_uses_business_order_not_alphabetical(self):
        expected = [self.crash.pk, self.refund.pk, self.question.pk]

        self.assertEqual(self.ids(ordering="-priority_rank"), expected)

    def test_invalid_filter_value_returns_400(self):
        response = self.client.get(LIST_URL, {"status": "not-a-status"})

        self.assertEqual(response.status_code, 400)

    def test_results_are_paginated(self):
        for number in range(12):
            make_ticket(self.customer, self.category, title=f"Extra ticket {number}")

        first_page = self.client.get(LIST_URL).data
        second_page = self.client.get(LIST_URL, {"page": 2}).data

        self.assertEqual(first_page["count"], 15)
        self.assertEqual(len(first_page["results"]), 10)
        self.assertEqual(len(second_page["results"]), 5)
        self.assertIsNone(second_page["next"])
