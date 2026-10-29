from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from tickets.models import Ticket

from . import tasks


@receiver(pre_save, sender=Ticket)
def remember_previous_state(sender, instance, **kwargs):
    """Store the saved status and assignee so post_save can tell what really changed."""
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values("status", "assigned_to_id").first()
    instance._previous_status = previous["status"] if previous else None
    instance._previous_assignee_id = previous["assigned_to_id"] if previous else None


@receiver(post_save, sender=Ticket)
def queue_ticket_emails(sender, instance, created, **kwargs):
    if created:
        schedule(tasks.notify_admins_of_new_ticket, instance.pk)
        return

    if instance.status != instance._previous_status:
        schedule(tasks.notify_customer_of_status_change, instance.pk, instance._previous_status)

    if instance.assigned_to_id and instance.assigned_to_id != instance._previous_assignee_id:
        schedule(tasks.notify_agent_of_assignment, instance.pk)


def schedule(task, *args):
    # Wait for the commit, otherwise the worker could read the ticket before it is saved.
    transaction.on_commit(lambda: task.delay(*args))
