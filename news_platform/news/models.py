"""Database models for the news application."""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """A user with a Reader, Editor, or Journalist role."""

    class Role(models.TextChoices):
        """The roles required by the project brief."""

        READER = "reader", "Reader"
        EDITOR = "editor", "Editor"
        JOURNALIST = "journalist", "Journalist"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.READER,
    )
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
    )
    profile_is_public = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    subscribed_publishers = models.ManyToManyField(
        "Publisher",
        blank=True,
        related_name="subscribers",
    )
    subscribed_journalists = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="journalist_subscribers",
        limit_choices_to={"role": Role.JOURNALIST},
    )


class Publisher(models.Model):
    """A publication that can employ multiple editors and journalists."""

    name = models.CharField(max_length=255, unique=True)
    editors = models.ManyToManyField(
        User,
        blank=True,
        related_name="editor_publishers",
        limit_choices_to={"role": User.Role.EDITOR},
    )
    journalists = models.ManyToManyField(
        User,
        blank=True,
        related_name="journalist_publishers",
        limit_choices_to={"role": User.Role.JOURNALIST},
    )

    def __str__(self):
        """Return the publisher name in Django's admin area."""
        return self.name


class Article(models.Model):
    """A news article from one independent journalist or one publisher."""

    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="independent_articles",
        limit_choices_to={"role": User.Role.JOURNALIST},
    )
    publisher = models.ForeignKey(
        Publisher,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="articles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        """Keep the article source valid even outside Django forms."""

        # The brief requires exactly one source for every article.
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(author__isnull=False, publisher__isnull=True)
                    | models.Q(author__isnull=True, publisher__isnull=False)
                ),
                name="article_has_one_source",
            ),
        ]

    def clean(self):
        """Explain an invalid article source choice in forms and admin."""
        super().clean()
        if bool(self.author) == bool(self.publisher):
            raise ValidationError(
                "An article must have either an independent author or a publisher."
            )

    def __str__(self):
        """Return the article title in Django's admin area."""
        return self.title


class Newsletter(models.Model):
    """A curated collection of articles created by a journalist or editor."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="newsletters",
        limit_choices_to={
            "role__in": [User.Role.JOURNALIST, User.Role.EDITOR],
        },
    )
    articles = models.ManyToManyField(Article, related_name="newsletters")

    def __str__(self):
        """Return the newsletter title in Django's admin area."""
        return self.title
