# ParkMe Account Management

ParkMe currently provides the required account feature: registration, login and logout, role-based dashboards, and private profile viewing and editing.

## Roles

- **Driver** is the default role assigned through public registration.
- **Administrator** is assigned to superusers created with Django's `createsuperuser` command.

Each role has its own protected dashboard. Users can only view and edit their own profile. Django's built-in authentication handles password hashing and session management.

Parking management features have been removed from the application. Existing parking tables and data in Supabase are left untouched; they are no longer used by this account-only version.

## Requirements

- Python 3.10 or newer
- PostgreSQL 14 or newer (local PostgreSQL or Supabase)

## Local setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`. In the Supabase dashboard, open **Project Settings → Database → Connection string** and use the database password for `DB_PASSWORD` (this is separate from the Supabase API keys). The project is configured for the Supabase PostgreSQL host, database `postgres`, port `5432`, and required TLS. If Supabase's direct connection is unavailable on your network, use the session pooler host, port, and username from its connection panel instead. Generate a private Django `SECRET_KEY` and keep both it and the database password in `.env`; `.env` is ignored by Git. Add the deployed HTTPS origin to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

4. Apply migrations to Supabase:

   ```bash
   python manage.py migrate
   ```

   Migrations create the account and Django framework tables. Django connects using its trusted server-side database connection; Supabase browser/client API keys are not used.

5. Create the first Administrator account in Supabase:

   ```bash
   python manage.py createsuperuser
   ```

6. Start the development server:

   ```bash
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000/`. Public registration creates Driver accounts; administrators are created through `createsuperuser`.

The Django application connects directly to PostgreSQL. Supabase's browser/client API keys are not used by this server-rendered Django backend and must not be put into templates, source code, or `.env` as database passwords. If a Supabase secret API key has been disclosed, rotate it in Supabase before using the project.

## Tests

Run the full test suite against the PostgreSQL database configured in `.env`:

```bash
python manage.py test
```

The tests cover required registration fields, email and username uniqueness, password confirmation and hashing, login/logout, role-based dashboard access, and private profile viewing and editing.

## GitHub preparation

Initialize and publish the project using a repository name that follows the course format, for example `ParkMe-Nacua-JohnBenedict-G01`. Confirm `.env` is not staged before pushing:

```bash
git init
git add .
git status --short
git commit -m "Set up ParkMe account feature"
```

Create a public GitHub repository, add it as `origin`, and push the initial branch. Never commit `.env` or real database credentials.
