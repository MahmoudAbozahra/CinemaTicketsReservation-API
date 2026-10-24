# Cinema Tickets Reservation API

A Django REST Framework API for managing guests, movies, and reservations.

## Local setup

Create and activate a virtual environment, then install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.text
```

Apply migrations and run the development server:

```powershell
python manage.py migrate
python manage.py runserver
```

When `DJANGO_DEBUG` is unset or true, Django generates an ephemeral development
secret if `DJANGO_SECRET_KEY` is absent. Set a local secret if sessions should
remain valid across process restarts.

`.env.example` documents the supported variables, but the project deliberately
does not add a dotenv dependency. Export the variables in the shell or configure
them in the process manager. For example:

```powershell
$env:DJANGO_DEBUG = "True"
$env:DJANGO_SECRET_KEY = "replace-with-a-local-random-secret"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
```

## Production configuration

When `DJANGO_DEBUG=False`, startup fails unless both `DJANGO_SECRET_KEY` and
`DJANGO_ALLOWED_HOSTS` are set. Production defaults also enable HTTPS redirects,
secure session and CSRF cookies, and one year of HTTP Strict Transport Security.
Only enable these settings when the application is served over HTTPS.

`DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` and `DJANGO_SECURE_HSTS_PRELOAD` remain
false unless explicitly enabled. Set them to true only after confirming every
subdomain is permanently HTTPS-only and the domain is ready for browser preload.

Use a unique random secret containing at least 50 characters. Never reuse the
placeholder from `.env.example`.

## Verification

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The repository ignores local SQLite databases. Django's test runner creates an
isolated test database and does not use the developer's `db.sqlite3` records.
