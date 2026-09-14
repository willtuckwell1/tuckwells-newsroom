"""Forms for creating and editing news content."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Article, Newsletter, Publisher, User


class RegistrationForm(UserCreationForm):
    """Create a public Reader or Journalist account."""

    PUBLIC_ROLE_CHOICES = [
        (User.Role.READER, "Reader"),
        (User.Role.JOURNALIST, "Journalist"),
    ]

    role = forms.ChoiceField(choices=PUBLIC_ROLE_CHOICES)

    class Meta:
        """Collect the safe fields needed to create a user account."""

        model = User
        fields = ["username", "email", "role", "password1", "password2"]

    def clean_email(self):
        """Prevent more than one account using the same email address."""
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


class ProfileForm(forms.ModelForm):
    """Allow users to update their profile and privacy preferences."""

    class Meta:
        """Expose editable profile and account-preference fields."""

        model = User
        fields = [
            "username",
            "email",
            "bio",
            "profile_picture",
            "profile_is_public",
            "show_email",
            "email_notifications",
        ]
        help_texts = {
            "profile_is_public": "Allow your profile and bio to be visible to readers.",
            "show_email": "Display your email address on your public profile.",
            "email_notifications": "Receive emails when followed content is approved.",
        }

    def clean_email(self):
        """Prevent an account from taking another user's email address."""
        email = self.cleaned_data["email"].lower()
        email_exists = User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk,
        ).exists()
        if email_exists:
            raise forms.ValidationError("An account already uses this email address.")
        return email


class PublisherForm(forms.ModelForm):
    """Allow an editor to create a publisher and staff it with people."""

    class Meta:
        """Expose the fields required to set up a publisher."""

        model = Publisher
        fields = ["name", "editors", "journalists"]
        help_texts = {
            "editors": "Editors who can review and approve this publisher's articles.",
            "journalists": "Journalists who can publish articles under this publisher.",
        }

    def __init__(self, *args, **kwargs):
        """Only offer real Editor and Journalist accounts as staff choices."""
        super().__init__(*args, **kwargs)
        self.fields["editors"].queryset = User.objects.filter(role=User.Role.EDITOR)
        self.fields["journalists"].queryset = User.objects.filter(
            role=User.Role.JOURNALIST,
        )


class ArticleForm(forms.ModelForm):
    """Collect article details while assigning its source safely."""

    class Meta:
        """Expose journalist-editable article fields only."""

        model = Article
        fields = ["title", "content", "publisher"]

    def __init__(self, *args, user, **kwargs):
        """Limit journalists to publishers with which they are affiliated."""
        super().__init__(*args, **kwargs)
        self.user = user

        if user.role == User.Role.JOURNALIST:
            self.fields["publisher"].queryset = user.journalist_publishers.all()

    def clean(self):
        """Set an independent article's author to the signed-in journalist."""
        cleaned_data = super().clean()
        publisher = cleaned_data.get("publisher")

        if publisher:
            # Publisher articles cannot also retain an independent author.
            self.instance.author = None
        elif not self.instance.pk or self.instance.author is None:
            if self.user.role == User.Role.JOURNALIST:
                self.instance.author = self.user

        if self.instance.author and self.instance.publisher:
            self.instance.publisher = None

        return cleaned_data


class NewsletterForm(forms.ModelForm):
    """Collect the title, description, and selected articles for a newsletter."""

    class Meta:
        """Expose the fields journalists and editors may manage."""

        model = Newsletter
        fields = ["title", "description", "articles"]

    def __init__(self, *args, **kwargs):
        """Explain how to populate the required curated-article selection."""
        super().__init__(*args, **kwargs)
        articles = self.fields["articles"]

        if articles.queryset.exists():
            articles.help_text = "Select one or more articles for this newsletter."
        else:
            articles.help_text = (
                "No articles are available yet. Create an article first, then return "
                "to add it to this newsletter."
            )
