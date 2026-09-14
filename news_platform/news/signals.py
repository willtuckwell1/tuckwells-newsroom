"""Signal handlers for role groups and their permissions."""

import logging

import requests
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.mail import send_mail
from django.db.models.signals import post_migrate, post_save, pre_save
from django.dispatch import receiver

from .models import Article, User


logger = logging.getLogger(__name__)


ROLE_PERMISSIONS = {
    User.Role.READER: [
        "view_article",
        "view_newsletter",
    ],
    User.Role.EDITOR: [
        "view_article",
        "change_article",
        "delete_article",
        "view_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ],
    User.Role.JOURNALIST: [
        "add_article",
        "view_article",
        "change_article",
        "delete_article",
        "add_newsletter",
        "view_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ],
}


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    """Create the task's role groups after the news models are migrated."""
    if sender.name != "news":
        return

    database = kwargs["using"]

    # Groups use Django's built-in model permissions for Article and Newsletter.
    for role, permission_codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.using(database).get_or_create(name=role.label)
        permissions = Permission.objects.using(database).filter(
            content_type__app_label="news",
            codename__in=permission_codenames,
        )
        group.permissions.set(permissions)


@receiver(post_save, sender=User)
def assign_user_to_role_group(instance, **kwargs):
    """Keep a user's assigned Django group in sync with their role."""
    if kwargs.get("raw", False):
        return

    role_group_names = [role.label for role in User.Role]
    instance.groups.remove(*Group.objects.filter(name__in=role_group_names))
    group, _ = Group.objects.get_or_create(name=User.Role(instance.role).label)
    instance.groups.add(group)

    if instance.role != User.Role.READER:
        # An empty many-to-many relation is Django's equivalent of None.
        instance.subscribed_publishers.clear()
        instance.subscribed_journalists.clear()


@receiver(pre_save, sender=Article)
def track_article_approval(instance, **kwargs):
    """Record whether an existing article is being approved in this save."""
    if kwargs.get("raw", False) or not instance.pk:
        instance.was_just_approved = False
        return

    previous_approval = Article.objects.filter(pk=instance.pk).values_list(
        "approved", flat=True
    ).first()
    instance.was_just_approved = not previous_approval and instance.approved


@receiver(post_save, sender=Article)
def notify_subscribers_of_approval(instance, created, **kwargs):
    """Email subscribers and notify the internal API after first approval."""
    if kwargs.get("raw", False) or created or not instance.was_just_approved:
        return

    if instance.author:
        subscribers = instance.author.journalist_subscribers
        source = instance.author.username
    else:
        subscribers = instance.publisher.subscribers
        source = instance.publisher.name

    recipient_list = list(
        subscribers.filter(
            role=User.Role.READER,
            email_notifications=True,
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )

    if recipient_list:
        try:
            send_mail(
                subject=f"New approved article: {instance.title}",
                message=(
                    f"{instance.title} has been approved and published by {source}."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
            )
        except Exception:
            logger.exception(
                "Unable to email subscribers about article %s",
                instance.pk,
            )

    try:
        response = requests.post(
            settings.ARTICLE_APPROVAL_API_URL,
            json={
                "article_id": instance.pk,
                "title": instance.title,
                "approved": instance.approved,
            },
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        # API failures are logged so an editor's approval remains successful.
        logger.exception(
            "Unable to notify the approved-article API for %s",
            instance.pk,
        )
