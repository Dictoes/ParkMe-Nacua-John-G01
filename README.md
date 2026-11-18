# ParkMe: Park, Snap and Return

ParkMe is a Django full-stack web application for helping drivers remember where they parked. It implements account registration and authentication, a shared facility and spot directory, personal vehicle and parking-session management, photo/note references, search, filters, and parking-history reports.

## Roles

- **Driver** is the default role assigned through public registration.
- **Administrator** is assigned to superusers created with Django's `createsuperuser` command. Administrators maintain the shared parking facility/spot directory and manage accounts.

The approved SDD identifies Drivers as the primary user. The Administrator role provides protected directory and account administration. Driver parking data remains private to its owner, including when another user is an administrator.

## Features from the approved SDD

- **Accounts:** driver registration and login, administrator account management, role-based dashboards, and private profile editing.
- **Vehicles:** add, view, update, and delete personally owned vehicles; plate numbers are unique per driver.
- **Facilities and locations:** maintain the shared facility directory and facility types; record a unique floor, zone, and stall for each facility.
- **Parking sessions:** record a vehicle, location, parked time, and Active/Completed status; complete, edit, search, filter, and delete a driver's own sessions.
- **Parking references:** upload a car/landmark photo, add notes, or both. Images are size/type validated and served only to the session owner.
- **History and reports:** filter by vehicle, facility, date, floor, zone, and status; view session totals by vehicle/facility/month and export the driver's own sessions to CSV.

Excluded SDD features such as GPS navigation, automatic vehicle detection, payments, and parking reservations are not implemented.

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

   Migrations create the Django account and ParkMe tables and enable PostgreSQL row-level security on application and Django framework tables, including `django_session`. No Supabase API-role policies grant access to these tables. Django continues to access them through its trusted server-side database connection.

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

The tests cover registration and password hashing, authentication and role access, profile ownership, vehicle/facility/location validation, full parking workflows, session ownership, reference validation, filtering, CSV reporting, and deletion constraints.

## GitHub preparation

Initialize and publish the project using a repository name that follows the course format, for example `ParkMe-Nacua-JohnBenedict-G01`. Confirm `.env` is not staged before pushing:

```bash
git init
git add .
git status --short
git commit -m "Set up ParkMe account feature"
```

Create a public GitHub repository, add it as `origin`, and push the initial branch. Never commit `.env` or real database credentials.
