"""Serializers that convert news application models to and from JSON."""

from rest_framework import serializers

from .models import Article, Newsletter, Publisher, User


class UserSerializer(serializers.ModelSerializer):
    """Represent a user without exposing their password."""

    class Meta:
        """Select safe user fields for API responses."""

        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "subscribed_publishers",
            "subscribed_journalists",
        ]
        read_only_fields = ["role"]


class PublisherSerializer(serializers.ModelSerializer):
    """Represent a publisher and its associated staff."""

    class Meta:
        """Select the fields returned for publishers."""

        model = Publisher
        fields = ["id", "name", "editors", "journalists"]


class ArticleSerializer(serializers.ModelSerializer):
    """Represent an article and validate its required source."""

    class Meta:
        """Select the fields returned for articles."""

        model = Article
        fields = [
            "id",
            "title",
            "content",
            "author",
            "publisher",
            "created_at",
            "approved",
        ]
        read_only_fields = ["author", "created_at", "approved"]

    def get_fields(self):
        """Allow only editors to change an article's approval status."""
        fields = super().get_fields()
        request = self.context.get("request")

        if request and (
            request.user.role == User.Role.EDITOR
            or request.user.groups.filter(name=User.Role.EDITOR.label).exists()
        ):
            fields["approved"].read_only = False

        return fields

    def validate(self, attributes):
        """Require every article to have one source, not both sources."""
        request = self.context.get("request")
        publisher = attributes.get(
            "publisher",
            getattr(self.instance, "publisher", None),
        )

        if self.instance is None and request:
            # An API journalist can only author an independent article as themself.
            if publisher is None:
                attributes["author"] = request.user
            elif not publisher.journalists.filter(pk=request.user.pk).exists():
                raise serializers.ValidationError(
                    "You can only submit an article for an affiliated publisher."
                )

        author = attributes.get("author", getattr(self.instance, "author", None))

        if bool(author) == bool(publisher):
            raise serializers.ValidationError(
                "An article must have either an independent author or a publisher."
            )

        return attributes


class NewsletterSerializer(serializers.ModelSerializer):
    """Represent a newsletter and the articles it curates."""

    class Meta:
        """Select the fields returned for newsletters."""

        model = Newsletter
        fields = ["id", "title", "description", "created_at", "author", "articles"]
        read_only_fields = ["created_at"]
