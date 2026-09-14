"""Automated REST API tests for the news application."""

from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .forms import ArticleForm, RegistrationForm
from .models import Article, Newsletter, Publisher, User
from .serializers import NewsletterSerializer


class AccountAndAccessTests(APITestCase):
    """Verify account security and page-level role protection."""

    def test_registration_hashes_password_and_assigns_reader_group(self):
        """New accounts never store the submitted password as plain text."""
        form = RegistrationForm(
            data={
                "username": "new-reader",
                "email": "new-reader@example.com",
                "role": User.Role.READER,
                "password1": "Secure-test-password-123",
                "password2": "Secure-test-password-123",
            }
        )

        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertNotEqual(user.password, "Secure-test-password-123")
        self.assertTrue(user.check_password("Secure-test-password-123"))
        self.assertTrue(user.groups.filter(name="Reader").exists())

    def test_reader_cannot_open_editor_review_page(self):
        """Readers must not access the editor approval workflow."""
        reader = User.objects.create_user(
            username="page-reader",
            password="test-password",
            role=User.Role.READER,
        )
        self.client.login(username=reader.username, password="test-password")

        response = self.client.get("/editor/articles/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_redirects_each_role_to_an_allowed_page(self):
        """Successful login must not send Readers to the Editor-only queue."""
        roles_and_destinations = [
            (User.Role.READER, "/"),
            (User.Role.JOURNALIST, "/dashboard/"),
            (User.Role.EDITOR, "/editor/articles/"),
        ]

        for index, (role, destination) in enumerate(roles_and_destinations):
            user = User.objects.create_user(
                username=f"login-user-{index}",
                password="test-password",
                role=role,
            )
            response = self.client.post(
                "/login/",
                {"username": user.username, "password": "test-password"},
            )

            self.assertRedirects(response, destination)
            self.client.logout()


class ArticleFormTests(APITestCase):
    """Verify defensive article-source validation in the web form."""

    def test_unaffiliated_publisher_is_rejected(self):
        """A Journalist cannot submit content for an unrelated publisher."""
        journalist = User.objects.create_user(
            username="form-journalist",
            password="test-password",
            role=User.Role.JOURNALIST,
        )
        publisher = Publisher.objects.create(name="Unrelated Publisher")

        form = ArticleForm(
            data={
                "title": "Invalid publisher article",
                "content": "This should be rejected.",
                "publisher": publisher.id,
            },
            user=journalist,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Select a valid choice", str(form.errors))


class PasswordResetTests(APITestCase):
    """Verify the secure forgot-password request flow."""

    @override_settings(
        MAILERS={
            "default": {
                "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
            },
        }
    )
    def test_password_reset_sends_secure_email(self):
        """A registered email receives a one-time reset link."""
        User.objects.create_user(
            username="reset-user",
            password="old-test-password",
            email="reset-user@example.com",
            role=User.Role.READER,
        )

        response = self.client.post(
            "/password-reset/",
            {"email": "reset-user@example.com"},
        )

        self.assertRedirects(response, "/password-reset/done/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset/", mail.outbox[0].body)
        self.assertIn("Password reset", mail.outbox[0].subject)


class ProfileSettingsTests(APITestCase):
    """Verify profile editing and authenticated password changes."""

    def setUp(self):
        """Create a user for account-settings tests."""
        self.user = User.objects.create_user(
            username="profile-user",
            password="Old-test-password-123",
            email="profile@example.com",
            role=User.Role.READER,
        )
        self.client.login(
            username="profile-user",
            password="Old-test-password-123",
        )

    def test_user_can_update_profile_and_privacy_settings(self):
        """Profile form data is saved to the authenticated user's account."""
        response = self.client.post(
            "/profile/",
            {
                "username": "profile-user",
                "email": "updated@example.com",
                "bio": "Independent reader and local news supporter.",
                "profile_is_public": "",
                "show_email": "on",
                "email_notifications": "",
            },
        )
        self.user.refresh_from_db()

        self.assertRedirects(response, "/profile/")
        self.assertEqual(self.user.bio, "Independent reader and local news supporter.")
        self.assertFalse(self.user.profile_is_public)
        self.assertTrue(self.user.show_email)
        self.assertFalse(self.user.email_notifications)

    def test_user_can_change_password(self):
        """Django accepts the current password and hashes the new password."""
        response = self.client.post(
            "/password-change/",
            {
                "old_password": "Old-test-password-123",
                "new_password1": "New-test-password-456",
                "new_password2": "New-test-password-456",
            },
        )
        self.user.refresh_from_db()

        self.assertRedirects(response, "/password-change/done/")
        self.assertTrue(self.user.check_password("New-test-password-456"))

    def test_private_profile_is_not_publicly_visible(self):
        """Turning off profile visibility prevents public profile access."""
        public_response = self.client.get(f"/profiles/{self.user.id}/")
        self.assertEqual(public_response.status_code, status.HTTP_200_OK)

        self.user.profile_is_public = False
        self.user.save()
        private_response = self.client.get(f"/profiles/{self.user.id}/")

        self.assertEqual(private_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reader_can_follow_and_unfollow_journalist(self):
        """Readers can control journalist subscriptions through the website."""
        journalist = User.objects.create_user(
            username="followed-journalist",
            password="test-password",
            role=User.Role.JOURNALIST,
        )

        follow_response = self.client.post(
            f"/subscriptions/journalists/{journalist.id}/toggle/"
        )
        self.assertRedirects(follow_response, "/profile/")
        self.assertTrue(
            self.user.subscribed_journalists.filter(pk=journalist.pk).exists()
        )

        self.client.post(f"/subscriptions/journalists/{journalist.id}/toggle/")
        self.assertFalse(
            self.user.subscribed_journalists.filter(pk=journalist.pk).exists()
        )

    def test_reader_can_follow_and_unfollow_publisher(self):
        """Readers can control publisher subscriptions through the website."""
        publisher = Publisher.objects.create(name="Followed Publisher")

        self.client.post(f"/subscriptions/publishers/{publisher.id}/toggle/")
        self.assertTrue(
            self.user.subscribed_publishers.filter(pk=publisher.pk).exists()
        )

        self.client.post(f"/subscriptions/publishers/{publisher.id}/toggle/")
        self.assertFalse(
            self.user.subscribed_publishers.filter(pk=publisher.pk).exists()
        )


class PublisherManagementTests(APITestCase):
    """Verify only editors can create, edit, and delete publishers."""

    def test_editor_can_create_publisher(self):
        """An editor can register a new publisher through the website."""
        editor = User.objects.create_user(
            username="publisher-editor",
            password="test-password",
            role=User.Role.EDITOR,
        )
        self.client.login(username=editor.username, password="test-password")

        response = self.client.post(
            "/publishers/create/",
            {"name": "Daily Gazette", "editors": [editor.id], "journalists": []},
        )

        self.assertRedirects(response, "/dashboard/")
        self.assertTrue(Publisher.objects.filter(name="Daily Gazette").exists())

    def test_journalist_cannot_create_publisher(self):
        """A journalist is blocked from registering a new publisher."""
        journalist = User.objects.create_user(
            username="publisher-journalist",
            password="test-password",
            role=User.Role.JOURNALIST,
        )
        self.client.login(username=journalist.username, password="test-password")

        response = self.client.post(
            "/publishers/create/",
            {"name": "Blocked Gazette", "editors": [], "journalists": []},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Publisher.objects.filter(name="Blocked Gazette").exists())


class NewsletterPageTests(APITestCase):
    """Verify that readers can browse newsletters and curated articles."""

    def test_reader_can_view_newsletter_and_curated_article(self):
        """Newsletter pages expose the curated collection to readers."""
        journalist = User.objects.create_user(
            username="newsletter-journalist",
            password="test-password",
            role=User.Role.JOURNALIST,
        )
        article = Article.objects.create(
            title="Curated article",
            content="Newsletter content.",
            author=journalist,
            approved=True,
        )
        newsletter = Newsletter.objects.create(
            title="Weekend edition",
            description="A thoughtful selection.",
            author=journalist,
        )
        newsletter.articles.add(article)

        list_response = self.client.get("/newsletters/")
        detail_response = self.client.get(f"/newsletters/{newsletter.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertContains(detail_response, article.title)


class ArticleApiTests(APITestCase):
    """Test authenticated article API access for every required role."""

    def setUp(self):
        """Create users and content shared by the API tests."""
        self.reader = User.objects.create_user(
            username="reader",
            password="test-password",
            email="reader@example.com",
            role=User.Role.READER,
        )
        self.journalist = User.objects.create_user(
            username="journalist",
            password="test-password",
            role=User.Role.JOURNALIST,
        )
        self.editor = User.objects.create_user(
            username="editor",
            password="test-password",
            role=User.Role.EDITOR,
        )
        self.other_journalist = User.objects.create_user(
            username="other-journalist",
            password="test-password",
            role=User.Role.JOURNALIST,
        )
        self.publisher = Publisher.objects.create(name="Daily News")
        self.publisher.journalists.add(self.journalist)
        self.followed_article = Article.objects.create(
            title="Followed article",
            content="Content from a followed journalist.",
            author=self.journalist,
            approved=True,
        )
        self.other_article = Article.objects.create(
            title="Other article",
            content="Content from an unfollowed journalist.",
            author=self.other_journalist,
            approved=True,
        )
        self.pending_article = Article.objects.create(
            title="Pending article",
            content="An article awaiting approval.",
            author=self.journalist,
        )
        self.reader.subscribed_journalists.add(self.journalist)

    def test_token_endpoint_returns_token_for_valid_credentials(self):
        """A valid username and password should return an API token."""
        response = self.client.post(
            "/api/token/",
            {"username": "reader", "password": "test-password"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_unauthenticated_user_cannot_view_articles(self):
        """Article endpoints require token authentication."""
        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_article_list_returns_only_approved_articles(self):
        """The article list hides content that an Editor has not approved."""
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {article["id"] for article in response.data},
            {self.followed_article.id, self.other_article.id},
        )

    def test_reader_can_only_retrieve_subscribed_articles(self):
        """A Reader receives approved articles from followed sources only."""
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/articles/subscribed/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([article["id"] for article in response.data], [
            self.followed_article.id,
        ])

    def test_reader_receives_articles_from_subscribed_publisher(self):
        """A Reader receives approved articles from a followed publisher."""
        publisher_article = Article.objects.create(
            title="Publisher article",
            content="Content from a followed publisher.",
            publisher=self.publisher,
            approved=True,
        )
        self.reader.subscribed_publishers.add(self.publisher)
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/articles/subscribed/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {article["id"] for article in response.data},
            {self.followed_article.id, publisher_article.id},
        )

    def test_reader_cannot_create_article(self):
        """Readers have view-only API access."""
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            "/api/articles/",
            {"title": "Blocked", "content": "Readers cannot create articles."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journalist_can_create_independent_article(self):
        """A Journalist can create an article and becomes its author."""
        self.client.force_authenticate(user=self.journalist)

        response = self.client.post(
            "/api/articles/",
            {"title": "New article", "content": "Journalist content."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.journalist.id)
        self.assertFalse(response.data["approved"])

    def test_approved_article_can_be_retrieved_by_id(self):
        """Authenticated users can retrieve a single approved article."""
        self.client.force_authenticate(user=self.reader)

        response = self.client.get(f"/api/articles/{self.followed_article.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.followed_article.title)

    @patch("news.signals.requests.post")
    @patch("news.signals.send_mail")
    def test_editor_can_approve_and_delete_article(self, mock_send_mail, mock_post):
        """An Editor can approve and delete while approval notifies subscribers."""
        mock_post.return_value.raise_for_status.return_value = None
        self.client.force_authenticate(user=self.editor)

        approval_response = self.client.put(
            f"/api/articles/{self.pending_article.id}/",
            {
                "title": self.pending_article.title,
                "content": self.pending_article.content,
                "approved": True,
            },
            format="json",
        )
        deletion_response = self.client.delete(
            f"/api/articles/{self.pending_article.id}/"
        )

        self.assertEqual(approval_response.status_code, status.HTTP_200_OK)
        self.assertTrue(approval_response.data["approved"])
        mock_send_mail.assert_called_once()
        mock_post.assert_called_once()
        self.assertEqual(deletion_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_newsletter_serializes_its_curated_articles(self):
        """A newsletter returns the articles included in its collection."""
        newsletter = Newsletter.objects.create(
            title="Weekly roundup",
            description="This week's selected articles.",
            author=self.journalist,
        )
        newsletter.articles.add(self.followed_article)

        serializer = NewsletterSerializer(newsletter)

        self.assertEqual(serializer.data["articles"], [self.followed_article.id])
