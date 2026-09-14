"""Application configuration for the news app."""

from importlib import import_module

from django.apps import AppConfig


class NewsConfig(AppConfig):
    """Configure the news application when Django starts."""

    name = 'news'

    def ready(self):
        """Load signal handlers for role groups and permissions."""
        import_module("news.signals")
