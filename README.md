# Cinema Tickets Reservation API

A small Django REST Framework project for managing movie listings, guest records, and reservations. It demonstrates token authentication, role based access, serializer validation, transactional writes, and automated quality checks. It is a learning and portfolio API, not a complete cinema booking platform.

## Supported functionality

- List, retrieve, search, and staff-manage movie records.
- Staff-only guest and reservation management.
- Create a reservation for a matching movie and hall; the API creates a guest and reservation together.
- Django admin for administrative data management.
- Token authentication for API requests.

## Technology and architecture

- Python 3.12, Django 5.2, Django REST Framework 3.18, SQLite, and Ruff.
- `project/` contains Django settings and root URL configuration. `tickets/` contains models, serializers, views, routes, and tests.
- DRF `ModelViewSet` and generic views expose the existing models; serializers define accepted and returned fields. The reservation endpoint validates input and writes records in one database transaction.
- Django migrations define the database schema. No additional service or repository layer is used.

## Prerequisites and installation

Use Python 3.12 and PowerShell (adapt activation commands for your shell). From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains pinned runtime dependencies. `requirements-dev.txt` installs those dependencies and Ruff. `requirements.text` remains as a compatibility file that includes `requirements.txt`.

## Environment and database

The application reads configuration from environment variables. `.env.example` lists the supported variables but is not loaded automatically; export them in your shell or configure them in your process manager. For local development:

```powershell
$env:DJANGO_DEBUG = "True"
$env:DJANGO_SECRET_KEY = "local-only-use-a-unique-random-secret-of-50-characters-or-more"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
```

Debug mode can generate a temporary secret when one is not supplied. Supply a local secret if you need sessions to survive restarts. For non-debug use, set a unique secret of at least 50 characters and explicit allowed hosts; startup rejects missing or weak values. Never use the example value in a deployed environment.

Initialize the local database and an administrator account:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

The repository does not include a database. SQLite is configured for local development; choose and configure a production database before deployment. Local database files are ignored by Git.

## Run the server

```powershell
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`; the admin site is at `/admin/`.

## Authentication and authorization

The API uses DRF token authentication. Create a user through Django admin or `createsuperuser`, then request a token with that user's username and password:

```http
POST /api-auth-token
Content-Type: application/json

{"username":"admin","password":"your-local-password"}
```

Successful response: `{"token":"<issued-token>"}`. Send it on protected requests as `Authorization: Token <issued-token>`. There is no public user registration endpoint. The project creates a token when a Django user is created.

| Operation | Access |
| --- | --- |
| Movie list, detail, and search | Authenticated user |
| Movie create, update, and delete | Staff user |
| Guest and reservation reads and writes | Staff user |
| Reservation creation endpoint | Staff user |
| Legacy guest JSON demonstrations | Staff user |
| Django admin | Active staff/superuser account |

Guest and reservation records have no user ownership relation in the schema, so the API restricts them to staff rather than implying per-user access. Anonymous API calls generally receive `401`; authenticated users without staff permission receive `403` for staff-only operations.

## API endpoint reference

All paths below are relative to the server root. Token auth is required unless stated otherwise.

| Method and path | Purpose | Access |
| --- | --- | --- |
| `POST /api-auth-token` | Obtain a token for an existing Django user | Public login endpoint |
| `GET /rest/viewsets/movie/` | List movies; supports `?search=<title>` | Authenticated |
| `GET /rest/viewsets/movie/{id}/` | Retrieve a movie | Authenticated |
| `POST /rest/viewsets/movie/` | Create movie (`hall`, `movie`, `date`) | Staff |
| `PUT/PATCH/DELETE /rest/viewsets/movie/{id}/` | Update or delete movie | Staff |
| `GET/POST /rest/viewsets/guests/` | List or create guests | Staff |
| `GET/PUT/PATCH/DELETE /rest/viewsets/guests/{id}/` | Retrieve or manage a guest | Staff |
| `GET/POST /rest/viewsets/reservations/` | List or create reservations (`guest`, `movie`) | Staff |
| `GET/PUT/PATCH/DELETE /rest/viewsets/reservations/{id}/` | Retrieve or manage a reservation | Staff |
| `GET /fbv/findmovie/?hall=A1&movie=Example` | Find movies matching both values | Authenticated |
| `POST /fbv/new_reservation` | Create guest and reservation atomically | Staff |
| `GET /django/jsonresponsenomodel/` | Legacy example JSON response | Staff |
| `GET /django/jsonresponsefrommodel/` | Legacy guest data response | Staff |
| `GET/POST /rest/{fbv_list,cbv_list,mixins_list,generics}/` | Legacy aliases for guest list/create | Staff |
| `GET/PUT/PATCH/DELETE /rest/{fbv_pk,CBV_pk,mixins_pk,generics}/{id}` | Legacy aliases for guest detail | Staff |

The legacy guest routes remain available for compatibility but all use the same generic guest views. The movie search filter matches the movie title; `findmovie` requires both hall and title. Movie search does not accept a date.

Compatibility notes: model serializers expose explicit fields, and the guest's reverse `reservation` field is read-only. Clients cannot assign reservations through guest writes. The reservation creation request continues to accept `name`, `mobile`, `hall`, and `movie`, and returns the canonical reservation fields `id`, `guest`, and `movie`.

## Example requests and responses

Create a movie as a staff user:

```http
POST /rest/viewsets/movie/
Authorization: Token <issued-token>
Content-Type: application/json

{"hall":"A1","movie":"Example Film","date":"2026-11-01"}
```

Create a reservation as a staff user:

```http
POST /fbv/new_reservation
Authorization: Token <issued-token>
Content-Type: application/json

{"name":"Sample Guest","mobile":"00000000000","hall":"A1","movie":"Example Film"}
```

Successful response (`201 Created`):

```json
{"id":1,"guest":1,"movie":1}
```

The request identifies a movie using the exact hall and title. No match or multiple matches return a validation error; the latter can occur because the endpoint does not accept a date or movie ID. Each successful request creates a new guest. No duplicate-booking rule is defined by this project.

## Tests and code quality

Run the Django checks and tests (Django's test runner uses an isolated test database):

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
```

Run Ruff lint and formatting checks:

```powershell
ruff check .
ruff format --check .
```

## GitHub Actions

The workflow in `.github/workflows/ci.yml` runs on pushes to `mahmoud` and pull requests targeting `main`. It installs the pinned development dependencies, checks dependency consistency, runs Ruff, Django and deployment checks, verifies migration consistency, and runs the test suite with synthetic configuration values. No production credentials are used.

## Security notes and scope limitations

Production mode requires explicit allowed hosts and a strong secret. It enables HTTPS redirection, secure cookies, and HSTS defaults; configure the application behind HTTPS before using these settings. HSTS subdomain and preload options require deliberate domain-wide readiness.

This project does not implement seat assignment, showtime scheduling, ticket inventory, payments, user-to-guest ownership, or duplicate reservation prevention. Deleting a guest or movie cascades to related reservations. SQLite is intended for local development, and the API does not currently define pagination. The misspelled `Guset` model name is retained to preserve the existing database/model compatibility.

Previously committed sensitive artifacts may remain in earlier Git history even though local databases and secrets are excluded from the current branch. Treat old Django secrets and any exposed account credentials or tokens as compromised and rotate them manually; do not commit replacement secrets.
