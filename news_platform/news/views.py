"""Views for the news application."""

import json
import logging

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied as ApiPermissionDenied
from rest_framework.response import Response

from .forms import (
    ArticleForm,
    NewsletterForm,
    ProfileForm,
    PublisherForm,
    RegistrationForm,
)
from .models import Article, Newsletter, Publisher, User
from .serializers import ArticleSerializer


logger = logging.getLogger(__name__)


class RoleBasedLoginView(LoginView):
    """Send each authenticated role to a page they are allowed to use."""

    def get_success_url(self):
        """Respect an explicit destination, then use the user's role."""
        redirect_url = self.get_redirect_url()
        if redirect_url:
            return redirect_url

        if is_editor(self.request.user):
            return reverse("editor_article_review")
        if is_journalist(self.request.user):
            return reverse("journalist_dashboard")
        return reverse("home")


def has_role_or_group(user, role):
    """Return whether a signed-in user has a role or its matching group."""
    return user.is_authenticated and (
        user.role == role or user.groups.filter(name=role.label).exists()
    )


def is_editor(user):
    """Return whether a user has the Editor role or belongs to its group."""
    return has_role_or_group(user, User.Role.EDITOR)


def is_journalist(user):
    """Return whether a user has the Journalist role or its matching group."""
    return has_role_or_group(user, User.Role.JOURNALIST)


def is_reader(user):
    """Return whether a user has the Reader role or its matching group."""
    return has_role_or_group(user, User.Role.READER)


def home(request):
    """Show all approved articles on the public news homepage."""
    articles = Article.objects.filter(approved=True).select_related(
        "author",
        "publisher",
    )
    return render(request, "news/home.html", {"articles": articles})


def public_article_detail(request, article_id):
    """Show one approved article to a reader."""
    article = get_object_or_404(
        Article.objects.select_related("author", "publisher"),
        pk=article_id,
        approved=True,
    )
    return render(request, "news/public_article_detail.html", {"article": article})


def public_profile(request, user_id):
    """Show a user's public profile when they have enabled profile visibility."""
    profile_user = get_object_or_404(
        User,
        pk=user_id,
        profile_is_public=True,
    )
    is_following = (
        request.user.is_authenticated
        and is_reader(request.user)
        and request.user.subscribed_journalists.filter(pk=profile_user.pk).exists()
    )
    return render(
        request,
        "news/public_profile.html",
        {"profile_user": profile_user, "is_following": is_following},
    )


def newsletter_list(request):
    """Show newsletters and their curated article counts to readers."""
    newsletters = Newsletter.objects.select_related("author").prefetch_related(
        "articles",
    )
    return render(request, "news/newsletter_list.html", {"newsletters": newsletters})


def newsletter_detail(request, newsletter_id):
    """Show one newsletter and its curated articles."""
    newsletter = get_object_or_404(
        Newsletter.objects.select_related("author").prefetch_related(
            "articles__author",
            "articles__publisher",
        ),
        pk=newsletter_id,
    )
    return render(request, "news/newsletter_detail.html", {"newsletter": newsletter})


@login_required
@require_POST
def toggle_journalist_subscription(request, user_id):
    """Subscribe or unsubscribe a Reader from an independent Journalist."""
    if not is_reader(request.user):
        raise PermissionDenied("Only Readers can manage subscriptions.")

    journalist = get_object_or_404(User, pk=user_id, role=User.Role.JOURNALIST)
    subscriptions = request.user.subscribed_journalists
    if subscriptions.filter(pk=journalist.pk).exists():
        subscriptions.remove(journalist)
    else:
        subscriptions.add(journalist)
    return redirect("profile_settings")


@login_required
@require_POST
def toggle_publisher_subscription(request, publisher_id):
    """Subscribe or unsubscribe a Reader from a Publisher."""
    if not is_reader(request.user):
        raise PermissionDenied("Only Readers can manage subscriptions.")

    publisher = get_object_or_404(Publisher, pk=publisher_id)
    subscriptions = request.user.subscribed_publishers
    if subscriptions.filter(pk=publisher.pk).exists():
        subscriptions.remove(publisher)
    else:
        subscriptions.add(publisher)
    return redirect("profile_settings")


def register(request):
    """Create and sign in a new Reader or Journalist account."""
    if request.user.is_authenticated:
        return redirect("home")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        if user.role == User.Role.JOURNALIST:
            return redirect("journalist_dashboard")
        return redirect("home")

    return render(request, "registration/register.html", {"form": form})


@login_required
def profile_settings(request):
    """Allow a signed-in user to edit profile and privacy settings."""
    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile_settings")

    return render(
        request,
        "registration/profile_settings.html",
        {
            "form": form,
            "publishers": Publisher.objects.all(),
            "journalists": User.objects.filter(role=User.Role.JOURNALIST),
        },
    )


@login_required
def editor_article_review(request):
    """Show unapproved articles to an authorized editor."""
    if not is_editor(request.user):
        raise PermissionDenied("Only editors can review articles.")

    pending_articles = Article.objects.filter(approved=False).select_related(
        "author",
        "publisher",
    )
    return render(
        request,
        "news/editor_article_review.html",
        {"pending_articles": pending_articles},
    )


@login_required
@require_POST
def approve_article(request, article_id):
    """Approve one article when the request is made by an authorized editor."""
    if not is_editor(request.user):
        raise PermissionDenied("Only editors can approve articles.")

    article = get_object_or_404(Article, pk=article_id)
    article.approved = True
    article.save()
    return redirect("editor_article_review")


@require_POST
def approved_article_log(request):
    """Accept and log an approved-article notification from the signal."""
    try:
        article_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    required_fields = {"article_id", "title", "approved"}
    if not required_fields.issubset(article_data):
        return JsonResponse({"detail": "Missing approved article data."}, status=400)

    logger.info("Approved article received by API: %s", article_data["article_id"])
    return JsonResponse({"detail": "Approved article logged."}, status=201)


@api_view(["GET", "POST"])
def article_list(request):
    """List approved articles or let a journalist submit a new article."""
    if request.method == "GET":
        approved_articles = Article.objects.filter(approved=True).select_related(
            "author",
            "publisher",
        )
        serializer = ArticleSerializer(approved_articles, many=True)
        return Response(serializer.data)

    if not is_journalist(request.user):
        raise ApiPermissionDenied("Only journalists can create articles.")

    serializer = ArticleSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    article = serializer.save()
    return Response(ArticleSerializer(article).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def subscribed_article_list(request):
    """Return approved articles from the authenticated Reader's subscriptions."""
    if not is_reader(request.user):
        raise ApiPermissionDenied("Only readers can retrieve subscribed articles.")

    subscribed_articles = Article.objects.filter(approved=True).filter(
        Q(author__in=request.user.subscribed_journalists.all())
        | Q(publisher__in=request.user.subscribed_publishers.all())
    ).select_related("author", "publisher").distinct()
    serializer = ArticleSerializer(subscribed_articles, many=True)
    return Response(serializer.data)


@api_view(["GET", "PUT", "DELETE"])
def article_detail(request, article_id):
    """Retrieve, update, or delete one approved article by its identifier."""
    article = get_object_or_404(Article, pk=article_id)

    if request.method == "GET":
        if not article.approved:
            raise ApiPermissionDenied("Only approved articles can be retrieved.")
        return Response(ArticleSerializer(article).data)

    if not (is_editor(request.user) or is_journalist(request.user)):
        raise ApiPermissionDenied("Only editors and journalists can change articles.")

    if request.method == "DELETE":
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ArticleSerializer(
        article,
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    updated_article = serializer.save()
    return Response(ArticleSerializer(updated_article).data)


def content_manager_articles(user):
    """Return articles that the signed-in editor or journalist may manage."""
    articles = Article.objects.select_related("author", "publisher")
    if is_editor(user):
        return articles

    return articles.filter(
        Q(author=user) | Q(publisher__in=user.journalist_publishers.all())
    )


def content_manager_newsletters(user):
    """Return newsletters that the signed-in editor or journalist may manage."""
    newsletters = Newsletter.objects.select_related("author")
    if is_editor(user):
        return newsletters

    return newsletters.filter(author=user)


def require_content_manager(user):
    """Reject requests from users without Editor or Journalist access."""
    if not (is_editor(user) or is_journalist(user)):
        raise PermissionDenied("Only editors and journalists can manage content.")


@login_required
def journalist_dashboard(request):
    """Show articles and newsletters available to a content manager."""
    require_content_manager(request.user)
    context = {
        "articles": content_manager_articles(request.user),
        "newsletters": content_manager_newsletters(request.user),
    }
    if is_editor(request.user):
        context["publishers"] = Publisher.objects.all()
    return render(request, "news/journalist_dashboard.html", context)


@login_required
def publisher_create(request):
    """Allow an editor to create a publisher and assign its staff."""
    if not is_editor(request.user):
        raise PermissionDenied("Only editors can create publishers.")

    form = PublisherForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/content_form.html",
        {"form": form, "page_title": "Create Publisher"},
    )


@login_required
def publisher_update(request, publisher_id):
    """Allow an editor to update a publisher's name and staff."""
    if not is_editor(request.user):
        raise PermissionDenied("Only editors can update publishers.")

    publisher = get_object_or_404(Publisher, pk=publisher_id)
    form = PublisherForm(request.POST or None, instance=publisher)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/content_form.html",
        {"form": form, "page_title": "Edit Publisher"},
    )


@login_required
def publisher_delete(request, publisher_id):
    """Allow an editor to delete a publisher."""
    if not is_editor(request.user):
        raise PermissionDenied("Only editors can delete publishers.")

    publisher = get_object_or_404(Publisher, pk=publisher_id)
    if request.method == "POST":
        publisher.delete()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/confirm_delete.html",
        {"object": publisher, "content_type": "Publisher"},
    )


@login_required
def article_create(request):
    """Allow a Journalist to create an independent or publisher article."""
    if not is_journalist(request.user):
        raise PermissionDenied("Only journalists can create articles.")

    form = ArticleForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/content_form.html",
        {"form": form, "page_title": "Create Article"},
    )


@login_required
def article_update(request, article_id):
    """Allow a content manager to update an available article."""
    require_content_manager(request.user)
    article = get_object_or_404(content_manager_articles(request.user), pk=article_id)
    form = ArticleForm(request.POST or None, instance=article, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/content_form.html",
        {"form": form, "page_title": "Edit Article"},
    )


@login_required
def article_delete(request, article_id):
    """Allow a content manager to delete an available article."""
    require_content_manager(request.user)
    article = get_object_or_404(content_manager_articles(request.user), pk=article_id)
    if request.method == "POST":
        article.delete()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/confirm_delete.html",
        {"object": article, "content_type": "Article"},
    )


@login_required
def newsletter_create(request):
    """Allow an Editor or Journalist to create a newsletter."""
    require_content_manager(request.user)
    form = NewsletterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        newsletter = form.save(commit=False)
        newsletter.author = request.user
        newsletter.save()
        form.save_m2m()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/content_form.html",
        {"form": form, "page_title": "Create Newsletter"},
    )


@login_required
def newsletter_update(request, newsletter_id):
    """Allow a content manager to update an available newsletter."""
    require_content_manager(request.user)
    newsletter = get_object_or_404(
        content_manager_newsletters(request.user),
        pk=newsletter_id,
    )
    form = NewsletterForm(request.POST or None, instance=newsletter)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/content_form.html",
        {"form": form, "page_title": "Edit Newsletter"},
    )


@login_required
def newsletter_delete(request, newsletter_id):
    """Allow a content manager to delete an available newsletter."""
    require_content_manager(request.user)
    newsletter = get_object_or_404(
        content_manager_newsletters(request.user),
        pk=newsletter_id,
    )
    if request.method == "POST":
        newsletter.delete()
        return redirect("journalist_dashboard")

    return render(
        request,
        "news/confirm_delete.html",
        {"object": newsletter, "content_type": "Newsletter"},
    )
