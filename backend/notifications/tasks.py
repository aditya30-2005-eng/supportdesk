import logging

from celery import shared_task

from tickets.models import Ticket

from . import emails

logger = logging.getLogger(__name__)

# SMTP errors are subclasses of OSError, so network and mail server problems get retried.
RETRY_OPTIONS = {
    "autoretry_for": (OSError,),
    "retry_backoff": True,
    "max_retries": 3,
}


def load_ticket(ticket_id):
    ticket = (
        Ticket.objects.select_related("category", "created_by", "assigned_to")
        .filter(pk=ticket_id)
        .first()
    )
    if ticket is None:
        logger.warning("Ticket %s no longer exists, skipping email", ticket_id)
    return ticket


@shared_task(**RETRY_OPTIONS)
def notify_admins_of_new_ticket(ticket_id):
    ticket = load_ticket(ticket_id)
    return emails.send_new_ticket_email(ticket) if ticket else 0


@shared_task(**RETRY_OPTIONS)
def notify_agent_of_assignment(ticket_id):
    ticket = load_ticket(ticket_id)
    if ticket is None or ticket.assigned_to is None:
        return 0
    return emails.send_assignment_email(ticket)


@shared_task(**RETRY_OPTIONS)
def notify_customer_of_status_change(ticket_id, old_status):
    ticket = load_ticket(ticket_id)
    return emails.send_status_change_email(ticket, old_status) if ticket else 0
