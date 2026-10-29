from django.core import mail
from django.test import TestCase

from notifications.tasks import notify_customer_of_status_change
from tickets.models import Ticket
from tickets.tests.helpers import SupportDeskTestCase, make_ticket


class TicketEmailTests(SupportDeskTestCase):
    """Signals queue Celery tasks after commit. In tests the tasks run eagerly into mail.outbox."""

    def setUp(self):
        super().setUp()
        with self.captureOnCommitCallbacks(execute=True):
            self.ticket = make_ticket(self.customer, self.category)
        mail.outbox.clear()

    def save_and_run_callbacks(self, **changes):
        for field, value in changes.items():
            setattr(self.ticket, field, value)
        with self.captureOnCommitCallbacks(execute=True):
            self.ticket.save()

    def test_new_ticket_emails_admins(self):
        with self.captureOnCommitCallbacks(execute=True):
            ticket = make_ticket(self.customer, self.category, title="Laptop will not boot")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
        self.assertIn(f"#{ticket.pk}", mail.outbox[0].subject)
        self.assertIn("Laptop will not boot", mail.outbox[0].body)

    def test_assignment_emails_the_agent(self):
        self.save_and_run_callbacks(assigned_to=self.agent)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["agent@example.com"])
        self.assertIn("assigned to you", mail.outbox[0].subject)

    def test_status_change_emails_the_customer(self):
        self.save_and_run_callbacks(status=Ticket.Status.IN_PROGRESS)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.com"])
        self.assertIn("from Open to In progress", mail.outbox[0].body)

    def test_saving_without_status_change_sends_nothing(self):
        self.save_and_run_callbacks(priority=Ticket.Priority.URGENT)
        self.save_and_run_callbacks(status=Ticket.Status.OPEN)

        self.assertEqual(mail.outbox, [])

    def test_reassigning_to_the_same_agent_sends_nothing(self):
        self.save_and_run_callbacks(assigned_to=self.agent)
        mail.outbox.clear()

        self.save_and_run_callbacks(assigned_to=self.agent)

        self.assertEqual(mail.outbox, [])

    def test_no_email_is_sent_if_the_transaction_rolls_back(self):
        # Without execute=True the on_commit callbacks are dropped, like after a rollback.
        with self.captureOnCommitCallbacks() as callbacks:
            self.ticket.status = Ticket.Status.CLOSED
            self.ticket.save()

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(mail.outbox, [])


class EmailThroughApiTests(SupportDeskTestCase):
    def test_full_flow_sends_one_email_per_event(self):
        self.login_as(self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/tickets/",
                {
                    "title": "Wi-Fi drops",
                    "description": "Every few minutes.",
                    "category": self.category.pk,
                },
            )
        ticket_url = f"/api/tickets/{response.data['id']}/"

        self.login_as(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f"{ticket_url}assign/", {"agent": self.agent.pk})

        self.login_as(self.agent)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(ticket_url, {"status": "resolved"})

        recipients = [message.to[0] for message in mail.outbox]
        self.assertEqual(
            recipients, ["admin@example.com", "agent@example.com", "customer@example.com"]
        )


class TaskTests(TestCase):
    def test_task_skips_missing_ticket(self):
        result = notify_customer_of_status_change.delay(999999, "open")

        self.assertEqual(result.get(), 0)
        self.assertEqual(mail.outbox, [])
