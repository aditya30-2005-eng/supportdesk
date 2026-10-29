import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tickets.models import Category, Comment, Ticket

User = get_user_model()

DEMO_PASSWORD = "Demo@12345"

USERS = [
    ("admin", "Asha", "Verma", User.Role.ADMIN),
    ("agent1", "Rahul", "Mehta", User.Role.AGENT),
    ("agent2", "Priya", "Nair", User.Role.AGENT),
    ("customer1", "Karan", "Shah", User.Role.CUSTOMER),
    ("customer2", "Neha", "Iyer", User.Role.CUSTOMER),
]

CATEGORIES = [
    ("Billing", "Invoices, payments and refunds"),
    ("Technical", "Bugs, errors and things that do not work"),
    ("Account", "Login, password and profile problems"),
    ("General", "Questions that do not fit anywhere else"),
]

# (title, description, category, priority, status, assigned agent index or None)
TICKETS = [
    (
        "Charged twice for October",
        "My card shows two payments for the same invoice.",
        "Billing",
        "high",
        "in_progress",
        0,
    ),
    (
        "Cannot download invoice PDF",
        "The download button does nothing on Chrome.",
        "Billing",
        "medium",
        "open",
        None,
    ),
    (
        "Refund not received",
        "I cancelled last week and the refund is still pending.",
        "Billing",
        "high",
        "resolved",
        1,
    ),
    (
        "Update GST number on invoices",
        "Please add my new GST number to future invoices.",
        "Billing",
        "low",
        "closed",
        0,
    ),
    (
        "App crashes on startup",
        "The mobile app closes right after the splash screen.",
        "Technical",
        "urgent",
        "in_progress",
        1,
    ),
    (
        "Export to CSV is empty",
        "The exported file only has the header row.",
        "Technical",
        "medium",
        "open",
        0,
    ),
    (
        "Page loads very slowly",
        "The reports page takes more than 20 seconds to load.",
        "Technical",
        "high",
        "open",
        None,
    ),
    (
        "Error 500 when saving profile",
        "Saving my profile shows a server error.",
        "Technical",
        "urgent",
        "resolved",
        0,
    ),
    (
        "Dark mode text is unreadable",
        "Some labels are dark grey on a black background.",
        "Technical",
        "low",
        "closed",
        1,
    ),
    (
        "Notifications not arriving",
        "I stopped getting email alerts two days ago.",
        "Technical",
        "medium",
        "in_progress",
        0,
    ),
    (
        "Forgot my password",
        "The reset link in the email has expired.",
        "Account",
        "medium",
        "resolved",
        1,
    ),
    (
        "Change account email",
        "I want to move my account to my work email.",
        "Account",
        "low",
        "open",
        None,
    ),
    (
        "Account locked after login attempts",
        "I typed the wrong password and now I am locked out.",
        "Account",
        "high",
        "resolved",
        0,
    ),
    (
        "Two-factor code not accepted",
        "The 6-digit code is always rejected.",
        "Account",
        "urgent",
        "open",
        1,
    ),
    (
        "Delete my old account",
        "Please remove the account I made by mistake.",
        "Account",
        "low",
        "closed",
        1,
    ),
    (
        "How do I add a team member?",
        "I could not find the invite option.",
        "General",
        "low",
        "resolved",
        0,
    ),
    (
        "Request for a product demo",
        "Our team would like a walkthrough of the reports.",
        "General",
        "medium",
        "open",
        None,
    ),
    (
        "Working hours of support",
        "Is support available on weekends?",
        "General",
        "low",
        "closed",
        0,
    ),
    (
        "Feature request: bulk upload",
        "It would help to upload many records at once.",
        "General",
        "medium",
        "open",
        None,
    ),
    (
        "Wrong timezone in reports",
        "Report times are 5.5 hours behind.",
        "Technical",
        "medium",
        "in_progress",
        1,
    ),
]

# A short conversation. Even positions are written by the agent, odd ones by the customer.
SAMPLE_COMMENTS = [
    "Thanks for reporting this. Could you share a screenshot of the problem?",
    "Sure, I have attached the screenshot. Please check.",
    "Thanks. This should be fixed now. Please try again and let us know.",
]


class Command(BaseCommand):
    help = "Create demo users, categories and about 20 sample tickets."

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(42)
        users = self.create_users()
        categories = self.create_categories()
        agents = [users["agent1"], users["agent2"]]
        customers = [users["customer1"], users["customer2"]]

        Ticket.objects.filter(created_by__in=customers).delete()
        tickets = self.create_tickets(rng, categories, agents, customers)
        self.add_comments(rng, tickets)

        self.stdout.write(self.style.SUCCESS(f"Created {len(tickets)} demo tickets."))
        self.stdout.write(f"All demo accounts use the password: {DEMO_PASSWORD}")

    def create_users(self):
        users = {}
        for username, first_name, last_name, role in USERS:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": f"{username}@supportdesk.local",
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "is_staff": role == User.Role.ADMIN,
                    "is_superuser": role == User.Role.ADMIN,
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            users[username] = user
        return users

    def create_categories(self):
        return {
            name: Category.objects.get_or_create(name=name, defaults={"description": text})[0]
            for name, text in CATEGORIES
        }

    def create_tickets(self, rng, categories, agents, customers):
        # bulk_create skips the post_save signal, so seeding does not send any emails.
        tickets = Ticket.objects.bulk_create(
            Ticket(
                title=title,
                description=description,
                category=categories[category],
                priority=priority,
                status=status,
                created_by=customers[index % 2],
                assigned_to=agents[agent] if agent is not None else None,
            )
            for index, (title, description, category, priority, status, agent) in enumerate(TICKETS)
        )
        self.spread_dates(rng, tickets)
        return tickets

    def spread_dates(self, rng, tickets):
        now = timezone.now()
        for ticket in tickets:
            created_at = now - timedelta(days=rng.randint(1, 30), hours=rng.randint(0, 23))
            resolved_at = None
            if ticket.status in Ticket.DONE_STATUSES:
                resolved_at = created_at + timedelta(hours=rng.randint(2, 72))
            ticket.created_at = created_at
            ticket.resolved_at = resolved_at
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=created_at, updated_at=resolved_at or created_at, resolved_at=resolved_at
            )

    def add_comments(self, rng, tickets):
        for ticket in tickets:
            if ticket.assigned_to is None:
                continue
            for position in range(rng.randint(1, 3)):
                author = ticket.assigned_to if position % 2 == 0 else ticket.created_by
                comment = Comment.objects.create(
                    ticket=ticket, author=author, message=SAMPLE_COMMENTS[position]
                )
                # created_at uses auto_now_add, so move it back in time with update().
                Comment.objects.filter(pk=comment.pk).update(
                    created_at=ticket.created_at + timedelta(hours=position + 1)
                )
