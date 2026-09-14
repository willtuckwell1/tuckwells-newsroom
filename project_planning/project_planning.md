# Project Planning

## Project Goal

Build a Django news application where readers can view approved articles from publishers and independent journalists, and subscribe to publishers and journalists for updates.

## User Roles

| Role | Main responsibilities |
| --- | --- |
| Reader | View articles and newsletters, and subscribe to publishers and journalists. |
| Journalist | Create, view, update, and delete articles and newsletters. |
| Editor | View, update, delete, review, and approve articles and newsletters. |

## Core Features

1. User login, token authentication, roles, groups, and permissions.
2. Publisher management, including its editors and journalists.
3. Articles from independent journalists or publishers.
4. Article review and approval by editors.
5. Newsletters that curate articles and are created or edited by journalists and editors.
6. Reader subscriptions to publishers and journalists.
7. Email notification and an internal API notification when an article is approved.
8. RESTful API endpoints for articles, including subscribed content.
9. Automated Django API tests, including successful and failed requests.
10. Profile management, privacy controls, secure password changes, and password resets.

## Functional Requirements: User Stories

### Reader

- As a reader, I want to browse a list of approved articles so that I can find news to read.
- As a reader, I want to open an article and read its full content, author, and publication date.
- As a reader, I want to view newsletters so that I can read curated collections of articles.
- As a reader, I want to subscribe to and unsubscribe from publishers and journalists so that I can follow their content.
- As a reader, I want the subscribed-content API endpoint to return articles only from the publishers and journalists I follow.
- As a reader, I want to create an account, edit my profile, and control my privacy settings.
- As a reader, I want to change my password or request a secure password-reset email.

### Journalist

- As a journalist, I want to create an article with a title and content so that an editor can review it.
- As a journalist, I want to create, view, update, and delete articles and newsletters.
- As a journalist, I want to publish articles independently or for an affiliated publisher.
- As a journalist, I want to create newsletters that contain selected articles.
- As a journalist, I want to create articles through the API using token authentication.
- As a journalist, I want to maintain a public profile with a biography and profile picture.

### Editor

- As an editor, I want to review and approve articles so that approved content becomes visible to readers.
- As an editor, I want to create publishers and assign their editors and journalists, so that journalists have a publisher to publish under.
- As an editor, I want to update and delete articles and newsletters.
- As an editor, I want an approval to email relevant subscribers and send an internal POST request to the approved-article API endpoint.
- As an editor, I want to approve and delete articles through the API.

### Account and Security

- Users can register as Readers or Journalists; Editor accounts are assigned securely by an administrator.
- Passwords are hashed using Django's built-in authentication system.
- Password-reset links are one-time, time-limited links sent by email.
- Authenticated users can change their password after confirming their current password.
- Users can edit their biography, profile picture, public-profile setting, email visibility, and notification preference.
- Login redirects users to a page appropriate to their role.

## Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| Security | Passwords must be handled by Django's built-in authentication system. API endpoints must use token authentication, and users must only access actions allowed by their role or group permissions. |
| Data protection | Only editors may approve articles. Readers must only retrieve approved articles and content from their own subscriptions. |
| Usability | Pages must have clear navigation, readable content, helpful form error messages, and work on desktop and mobile screens. |
| Reliability | Invalid form submissions must not save incomplete or incorrect data. Article approval status must persist after restarting the application. |
| Performance | Article lists and subscribed-content API requests should return promptly for the expected project data volume. |
| Maintainability | Use Django models, forms, templates, URL names, serializers, and tests with clear, consistent names. Code must follow PEP 8 and be modular. |
| Accessibility | Forms must have labels, images must have alternative text, and content must remain readable with good colour contrast. |

## Main Data

| Item | Key information |
| --- | --- |
| User | Username, email, password, role, groups, publisher subscriptions, journalist subscriptions. |
| Publisher | Name, editors, journalists. |
| Article | Title, content, author, publisher, creation date, approval status. |
| Newsletter | Title, description, author, creation date, selected articles. |
| Profile settings | Biography, profile picture, public visibility, email visibility, email notifications. |

## Required Models and Relationships

### Custom User

- Extends Django's `AbstractUser`.
- Has a `role` field with `Reader`, `Editor`, and `Journalist` choices.
- Is assigned to the matching Django group when created.
- Reader users have many-to-many subscriptions to `Publisher` and to Journalist `User` accounts.
- Journalist users use the reverse relationships from `Article` and `Newsletter` to access their independent content.
- Where a field does not apply to the user's role, it is left empty.

### Publisher

- Has a name.
- Has many-to-many relationships to Editor users and Journalist users.
- Can have multiple editors and journalists.

### Article

- Includes `title`, `content`, `author`, `created_at`, `approved`, and `publisher` fields.
- `author` links to a Journalist user for an independent article.
- `publisher` links to a Publisher for publisher content.
- Validation must ensure an article belongs to either an independent journalist or a publisher.
- `approved` is a Boolean field, changed by an editor during review.

### Newsletter

- Includes `title`, `description`, `created_at`, and `author` fields.
- Is created by a journalist or editor.
- Has a many-to-many relationship to `Article` so it can curate multiple articles.
- Readers can view newsletters; journalists and editors can create or edit them.
- Readers can browse newsletter lists and open individual curated collections.

### Subscriptions

- Readers can follow or unfollow independent journalists.
- Readers can follow or unfollow publishers.
- Approval emails respect each Reader's email-notification preference.

## Group Permissions

| Group | Articles | Newsletters |
| --- | --- | --- |
| Reader | View only | View only |
| Editor | View, update, delete, and approve | View, update, and delete |
| Journalist | Create, view, update, and delete | Create, view, update, and delete |

## API Plan

Use Django REST Framework serializers for `Article`, `User`, `Newsletter`, and `Publisher`. Protect the API with token authentication and role-based permissions.

| Method | Endpoint | Access and behaviour |
| --- | --- | --- |
| `GET` | `/api/articles/` | Return all approved articles. |
| `GET` | `/api/articles/subscribed/` | Return approved articles from the authenticated reader's subscribed publishers and journalists. |
| `GET` | `/api/articles/<id>/` | Return one article. |
| `POST` | `/api/articles/` | Create an article; journalists only. |
| `PUT` | `/api/articles/<id>/` | Update an article; editors and journalists only. |
| `DELETE` | `/api/articles/<id>/` | Delete an article; editors and journalists only. |
| `POST` | `/api/approved/` | Receive and log the notification sent after an article is approved. |

## Approval Notification Plan

Use Django signals. When an editor changes an article to approved:

1. Email subscribers of the article's journalist or publisher.
2. Send a POST request with the approved article data to `/api/approved/` using Python's `requests` module.

## Testing Plan

Write Django automated tests for successful and failed requests. Cover authentication and role access, reader subscription filtering, journalist article creation, editor approval and deletion, newsletter pages, registration, profile privacy, password changes, password resets, and the approval signal using mocked email and HTTP requests.

## Design Diagrams

- `ClassDiagramNewsApplication.png` documents the Django models and relationships.
- `UseCaseDiagramNewsApplication.png` documents Reader, Journalist, and Editor actions.
- `SequenceDiagramNewsApplication.png` documents article approval, email, and API notification flow.

## Development Order

1. [x] Create the Django project and `news` app.
2. [x] Configure a custom user model, groups, and permissions before the first migration.
3. [x] Create and normalise the Publisher, Article, and Newsletter models, including their relationships.
4. [x] Create and apply the initial database migrations for development.
5. [x] Build the login page, editor review templates, views, URL paths, and role-based access control.
6. [x] Build the journalist content-management workflows for articles and newsletters.
7. [x] Add approval notifications using Django signals: email subscribers and POST to `/api/approved/`.
8. [x] Build the token-authenticated REST API, serializers, permissions, and required endpoints.
9. [x] Write automated API tests for success and failure cases, including mocked notification behaviour.
10. [x] Plan and implement the UI/UX, validate input and errors defensively.
11. [x] Migrate the final database from SQLite to MariaDB and complete submission checks.
12. [x] Add registration, password reset/change, profile settings, privacy controls, public profiles, newsletter pages, and subscription management.

## Reviewer Feedback Addressed

- Configuration is now handled by one consistent method: `python-dotenv` loads a local `.env` file (copied from `.env.example`) in `settings.py`, and `requirements.txt` lists `python-dotenv` as a dependency. The README no longer mixes this with manual `export` commands.
- Registration was blocked because there was no way to create a Publisher. Editors can now create, edit, and delete publishers from the Dashboard, and assign Editors and Journalists to each publisher, unblocking the full Journalist and Editor workflow.

## Code Quality Checklist

- [x] Python source compiles successfully.
- [x] Django system checks report no issues.
- [x] Automated tests pass, including successful and failed requests.
- [x] 21 automated tests pass against MariaDB.
- [x] Pylance reports no diagnostics.
- [x] Python files use four-space indentation with no tab characters.
- [x] Python source stays within the selected 88-character line limit.
- [x] Forms validate account data, passwords, article sources, and publisher affiliation.
- [x] Access control protects Reader, Journalist, and Editor workflows.
- [x] Password reset, password change, profile privacy, newsletter, and subscription workflows are tested.
- [x] Run the final checks again after the MariaDB migration.

