# Tuckwells Newsroom

Tuckwells Newsroom is a Django news application. Readers can view approved news articles and follow publishers or independent journalists. Journalists can create articles and newsletters. Editors review articles before they become visible to readers.

This project was created for the HyperionDev Capstone Project - News Application.

## What The Application Does

The application has three types of users:

- **Reader**: views approved articles and newsletters, and follows publishers or journalists.
- **Journalist**: creates and manages articles and newsletters.
- **Editor**: reviews and approves articles before publication.

The application also includes:

- Secure account registration and login.
- Profile editing with biography, profile picture, privacy, and email settings.
- Optional public profiles with controllable email visibility.
- Authenticated password changes from the profile area.
- Secure password hashing through Django.
- Forgot-password email reset links.
- Role-based Django groups and permissions.
- Publishers with multiple journalists and editors.
- Articles from independent journalists or publishers.
- Newsletters containing selected articles.
- Email and internal API notifications after article approval.
- A token-authenticated REST API.
- Automated tests.
- MariaDB database support.
- Responsive web pages for desktop and mobile screens.

## Project Structure

```text
News Application Capstone Project/
├── README.md
├── requirements.txt
├── .env.example
├── ClassDiagramNewsApplication.png
├── UseCaseDiagramNewsApplication.png
├── SequenceDiagramNewsApplication.png
├── project_planning/
│   └── project_planning.md
└── news_platform/
    ├── manage.py
    ├── db.sqlite3                 # Old local database, excluded from Git
    ├── news_platform/
    │   ├── settings.py            # Main Django configuration
    │   └── urls.py                # Project-level URLs
    └── news/
        ├── models.py              # Users, publishers, articles, newsletters
        ├── forms.py               # Website forms and validation
        ├── views.py               # Website and API actions
        ├── serializers.py         # Converts API data to and from JSON
        ├── signals.py             # Groups, permissions, and approval notices
        ├── urls.py                # News application URLs
        ├── tests.py               # Automated tests
        └── templates/             # HTML pages
```

## Requirements

You need:

- macOS, Linux, or Windows.
- Python 3.12 or newer.
- MariaDB 10.6 or newer. MariaDB 12 has also been tested.
- A terminal and a web browser.

## First-Time Setup

The commands below are run from the main project folder:

```bash
cd "~/Documents/News Application Capstone Project"
```

### 1. Create or activate the virtual environment

A virtual environment keeps this project's Python packages separate from other projects.

If `.venv` does not exist, create it:

```bash
python3 -m venv .venv
```

Activate it when using a normal terminal:

```bash
source .venv/bin/activate
```

You can also use `.venv/bin/python` directly, which is what the commands in this README use.

### 2. Install the project packages

```bash
.venv/bin/python -m pip install -r requirements.txt
```

### 3. Start MariaDB

On macOS with Homebrew:

```bash
brew services start mariadb
```

If MariaDB is already running, this command is not needed.

### 4. Create the MariaDB database

Log in to MariaDB with an administrator account. The exact command depends on how MariaDB was installed. Then run:

```sql
CREATE DATABASE tuckwells_newsroom CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tuckwells_news'@'localhost' IDENTIFIED BY 'choose-a-local-password';
GRANT ALL PRIVILEGES ON tuckwells_newsroom.* TO 'tuckwells_news'@'localhost';
FLUSH PRIVILEGES;
```

If the database or user already exists, do not create it again. Use the existing details instead.

### 5. Set up your local environment file

Django reads database settings from a `.env` file using `python-dotenv`, which is installed as part of `requirements.txt`. Copy the example file and edit it with your own local values:

```bash
cp .env.example .env
```

Open `.env` and replace the password with the password you chose when creating the MariaDB user:

```text
DB_NAME=tuckwells_newsroom
DB_USER=tuckwells_news
DB_PASSWORD=choose-a-local-password
DB_HOST=localhost
DB_PORT=3306
```

`.env` is excluded from Git by `.gitignore`, so your password is never committed. Every `manage.py` command below automatically loads `.env` from the project folder; you do not need to export these variables yourself.

### 6. Apply the database migrations

A migration creates the tables Django needs for users, groups, articles, publishers, newsletters, subscriptions, and API tokens.

```bash
.venv/bin/python news_platform/manage.py migrate
```

### 7. Check the project

```bash
.venv/bin/python news_platform/manage.py check
```

A successful check ends with:

```text
System check identified no issues (0 silenced).
```

## Create Users

### Create a Reader or Journalist

Open the website and select **Create account**. Choose either Reader or Journalist.

```text
http://127.0.0.1:8000/register/
```

Passwords are processed by Django's secure password-hashing system. The original password is not stored in the database.

### Create an Editor for local testing

Editor accounts cannot be created from the public registration page. This prevents anyone from giving themselves approval powers.

Create an Editor from the Django shell instead:

```bash
.venv/bin/python news_platform/manage.py shell
```

Then enter:

```python
from news.models import User
User.objects.create_user(
    username="editor1",
    email="editor@example.com",
    password="choose-a-strong-password",
    role=User.Role.EDITOR,
)
```

Exit the shell with:

```python
exit()
```

The user is automatically placed in the `Editor` group.

## Start The Website

From the main project folder, with `.env` set up as described above:

```bash
.venv/bin/python news_platform/manage.py runserver
```

Open this address in your browser:

```text
http://127.0.0.1:8000/
```

Stop the server with `Control + C` in the terminal where it is running.

## Main Website Workflows

### Reader

1. Open the homepage.
2. Select an article to read it.
3. Create a Reader account if you want to use reader features.
4. Sign in using the login page.
5. Use **Forgot your password?** if you need a reset link.
6. Open **Profile** to edit your username, email, biography, profile picture, privacy choices, and email notifications.
7. Use **Change password** from Profile when you want to update your password.
8. Use **Newsletters** to browse curated collections, and use **Profile** to follow or unfollow journalists and publishers.

During local development, password-reset emails are printed in the terminal because Django uses its console email backend. A real email service should be configured before production use.

### Journalist

1. Create a Journalist account.
2. Sign in.
3. Open the **Dashboard**.
4. Select **Create article**.
5. Create an independent article by leaving Publisher empty, or choose a publisher an Editor has affiliated you with.
6. Create a newsletter and select articles for its curated collection.
7. Edit or delete your content from the dashboard.
8. Wait for an Editor to approve an article before it appears publicly.

### Editor

1. Sign in using an Editor account.
2. Open the **Dashboard** and select **Create publisher** to register a new publisher.
3. When creating or editing a publisher, select the Editors and Journalists who work for it. A journalist must be added to a publisher here before they can publish articles under that publisher.
4. Open **Review queue**.
5. Read the submitted article.
6. Select **Approve article**.
7. The article becomes public.
8. Subscribers are emailed and the approval is sent to the internal `/api/approved/` endpoint.

## REST API

The API uses Django REST Framework token authentication.

### Get an API token

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -d "username=reader1" \
  -d "password=your-password"
```

Copy the token from the response and use it as follows:

```bash
curl http://127.0.0.1:8000/api/articles/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### Required article endpoints

| Method | URL | Purpose |
| --- | --- | --- |
| GET | `/api/articles/` | Return all approved articles. |
| GET | `/api/articles/subscribed/` | Return approved articles from the Reader's subscriptions. |
| GET | `/api/articles/<id>/` | Return one approved article. |
| POST | `/api/articles/` | Create an article as a Journalist. |
| PUT | `/api/articles/<id>/` | Update an article as an Editor or Journalist. |
| DELETE | `/api/articles/<id>/` | Delete an article as an Editor or Journalist. |
| POST | `/api/approved/` | Receive the internal approval notification. |

Readers can view only. Journalists can create articles. Editors can approve and delete articles.

## Run The Automated Tests

Tests use a temporary test database, so they do not delete your normal MariaDB data.

```bash
.venv/bin/python news_platform/manage.py test news
```

The suite checks authentication, roles, subscriptions, article permissions, newsletters, registration, password reset, approval notifications, and failed requests.

## Design Documentation

The project folder includes three diagrams created for the assignment:

- `ClassDiagramNewsApplication.png`: the Django models and their relationships.
- `UseCaseDiagramNewsApplication.png`: the actions available to each user role.
- `SequenceDiagramNewsApplication.png`: the Editor approval, email, and internal API flow.

## Security Notes

- Passwords are hashed using Django's built-in authentication system.
- Password reset links are one-time and expire.
- Editor accounts are not publicly selectable during registration.
- API endpoints require token authentication.
- CSRF protection is enabled on website forms.
- Article sources are validated so an article belongs to one source: a Journalist or a Publisher.
- Only editors can create, edit, or delete publishers and assign their staff.
- Database credentials are supplied through a local `.env` file, which is excluded from Git.
- Never commit `.env`, passwords, tokens, or production credentials.

## Final Checks Before Submission

```bash
.venv/bin/python -m pip check
.venv/bin/python news_platform/manage.py check
.venv/bin/python news_platform/manage.py test news
python3 -m compileall -q news_platform
```

Also check that:

- The MariaDB service is running.
- All required files are inside the project folder.
- `.env` and passwords are excluded from Git.
- No temporary test users or articles remain in the database.
- The project-planning document is included with the submission.
