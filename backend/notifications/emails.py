from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

User = get_user_model()


def ticket_link(ticket):
    return f"{settings.FRONTEND_URL}/tickets/{ticket.pk}"


def send_new_ticket_email(ticket):
    recipients = list(
        User.objects.filter(role=User.Role.ADMIN, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        return 0
    body = (
        f"A new ticket was raised by {ticket.created_by.username}.\n\n"
        f"Title: {ticket.title}\n"
        f"Category: {ticket.category.name}\n"
        f"Priority: {ticket.get_priority_display()}\n\n"
        f"Assign it here: {ticket_link(ticket)}\n"
    )
    return send_mail(f"[SupportDesk] New ticket #{ticket.pk}", body, None, recipients)


def send_assignment_email(ticket):
    agent = ticket.assigned_to
    body = (
        f"Hi {agent.first_name or agent.username},\n\n"
        f"Ticket #{ticket.pk} has been assigned to you.\n\n"
        f"Title: {ticket.title}\n"
        f"Priority: {ticket.get_priority_display()}\n"
        f"Customer: {ticket.created_by.username}\n\n"
        f"Open the ticket: {ticket_link(ticket)}\n"
    )
    return send_mail(
        f"[SupportDesk] Ticket #{ticket.pk} assigned to you", body, None, [agent.email]
    )


def send_status_change_email(ticket, old_status):
    customer = ticket.created_by
    old_label = dict(ticket.Status.choices).get(old_status, old_status)
    body = (
        f"Hi {customer.first_name or customer.username},\n\n"
        f'The status of your ticket "{ticket.title}" changed '
        f"from {old_label} to {ticket.get_status_display()}.\n\n"
        f"View the ticket: {ticket_link(ticket)}\n"
    )
    return send_mail(
        f"[SupportDesk] Ticket #{ticket.pk} is now {ticket.get_status_display()}",
        body,
        None,
        [customer.email],
    )
