"""URL routes for the news application."""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("profile/", views.profile_settings, name="profile_settings"),
    path("newsletters/", views.newsletter_list, name="newsletter_list"),
    path(
        "newsletters/<int:newsletter_id>/",
        views.newsletter_detail,
        name="newsletter_detail",
    ),
    path("register/", views.register, name="register"),
    path(
        "editor/articles/",
        views.editor_article_review,
        name="editor_article_review",
    ),
    path(
        "editor/articles/<int:article_id>/approve/",
        views.approve_article,
        name="approve_article",
    ),
    path(
        "api/approved/",
        views.approved_article_log,
        name="approved_article_log",
    ),
    path("api/token/", obtain_auth_token, name="api_token"),
    path("api/articles/", views.article_list, name="article_list"),
    path(
        "api/articles/subscribed/",
        views.subscribed_article_list,
        name="subscribed_article_list",
    ),
    path("api/articles/<int:article_id>/", views.article_detail, name="article_detail"),
    path("dashboard/", views.journalist_dashboard, name="journalist_dashboard"),
    path("publishers/create/", views.publisher_create, name="publisher_create"),
    path(
        "publishers/<int:publisher_id>/edit/",
        views.publisher_update,
        name="publisher_update",
    ),
    path(
        "publishers/<int:publisher_id>/delete/",
        views.publisher_delete,
        name="publisher_delete",
    ),
    path("articles/create/", views.article_create, name="article_create"),
    path(
        "articles/<int:article_id>/edit/",
        views.article_update,
        name="article_update",
    ),
    path(
        "articles/<int:article_id>/delete/",
        views.article_delete,
        name="article_delete",
    ),
    path("newsletters/create/", views.newsletter_create, name="newsletter_create"),
    path(
        "newsletters/<int:newsletter_id>/edit/",
        views.newsletter_update,
        name="newsletter_update",
    ),
    path(
        "newsletters/<int:newsletter_id>/delete/",
        views.newsletter_delete,
        name="newsletter_delete",
    ),
    path(
        "articles/<int:article_id>/read/",
        views.public_article_detail,
        name="public_article_detail",
    ),
    path(
        "profiles/<int:user_id>/",
        views.public_profile,
        name="public_profile",
    ),
    path(
        "subscriptions/journalists/<int:user_id>/toggle/",
        views.toggle_journalist_subscription,
        name="toggle_journalist_subscription",
    ),
    path(
        "subscriptions/publishers/<int:publisher_id>/toggle/",
        views.toggle_publisher_subscription,
        name="toggle_publisher_subscription",
    ),
]
