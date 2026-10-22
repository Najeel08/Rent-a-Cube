# Rent-a-Cube

Rent-a-Cube is a Django application for finding and booking coworking spaces.
It has separate portals for customers, workspace owners, technicians and platform
administrators.

## Features

- Customers can search spaces, book a time slot, pay, message owners and request service.
- Owners can manage spaces, bookings, refunds and technician assignments.
- Technicians can view and accept or reject assigned service requests.
- Platform administrators approve owners and review platform records and support inquiries.

## Technology

Python 3.13, Django 5.2, SQLite, HTML, CSS and JavaScript. Razorpay handles online
payments. Django handles templates, sessions, password hashing and email.

## Project structure

```text
manage.py                  Django command-line entry point
requirements.txt           Python dependencies
config/                    Settings, URLs and shared helpers
home/                      Landing page and support inquiries
accounts/                  Customers, bookings, chat and payments
owners/                    Owners, spaces and technician management
technicians/               Technician portal
admin_portal/              Platform administrator portal
templates/                 HTML pages grouped by portal
static/                    CSS, JavaScript, fonts and images
```

## Run locally on Windows

Install Python 3.13 and Git first. Open a terminal in the `Rent-a-Cube` directory
containing `manage.py`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Paste the generated key into `DJANGO_SECRET_KEY` in `.env`. Keep that key stable.
For an existing installation, keep the existing environment and `.env` instead
of recreating or overwriting them. Back up existing data before migrating.

The example file contains local development settings and empty payment keys.
Edit `.env` with your own settings; never put real credentials in `.env.example`
or commit `.env`. Settings supplied by the environment take priority over `.env`.
The generated Django key keeps login sessions secure; it is not a payment key.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open **http://127.0.0.1:8000/**. These commands use the project environment directly;
activation is optional. Always apply pending migrations before starting Django.
For another port, use `manage.py runserver 8001`.

To recreate the environment later, stop the server, delete only `.venv`, and repeat
the environment creation and requirements-install commands above. Keep `.env`,
`db.sqlite3`, `media/`, `private_media/` and all migration files. Recreating the
environment does not require resetting the database or creating users again.

## Accounts and demonstration

| Role | Sign-in page | How the account is created |
|---|---|---|
| Customer | `/accounts/sign-in/` | Public registration |
| Owner | `/owners/sign-in/` | Public registration, then platform-admin approval |
| Technician | `/technicians/sign-in/` | Owner creates the account and sends a password-setup link |
| Platform administrator | `/admin-portal/sign-in/` | Create a PlatformAdmin record through Django admin |
| Django administrator | `/admin/` | Run the command below |

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Django-admin and platform-admin credentials are separate. For a demonstration,
create a platform administrator, approve an owner, add a space, then register a
customer and book it. An approved owner can also add and assign a technician.
Without SMTP configuration, technician setup emails appear in the server console.
Do not commit those links or use real personal documents as demo data.

For real payments, configure the Razorpay keys in `.env`. For local demonstration
only, `ALLOW_DEMO_PAYMENTS=True` works when `DJANGO_DEBUG=True`; it does not charge
money. Without keys or explicit demo mode, checkout remains disabled. Demo mode
is always disabled in production.

Before publishing the repository, review `git status` for private files.

## Production settings

The example `.env` is for local development. On your hosting service, set these
environment variables instead of copying local HTTP settings:

| Variable | Production value |
|---|---|
| `DJANGO_LOAD_ENV` | `0` (prevents loading the local development `.env`) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | Your strong, stable secret from the hosting service's secret settings |
| `DJANGO_ALLOWED_HOSTS` | Your actual hostname(s), separated by commas; no wildcard |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000`, after HTTPS is working |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` until all subdomains use HTTPS |
| `DJANGO_SECURE_HSTS_PRELOAD` | `False` until you deliberately enable preload |
| `DJANGO_SESSION_COOKIE_SECURE` | `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | `True` |
| `ALLOW_DEMO_PAYMENTS` | `False` |

Use a production server and HTTPS. If HTTPS ends at a trusted reverse proxy,
configure it to strip untrusted forwarded headers before enabling
`DJANGO_USE_X_FORWARDED_PROTO`. Verify all subdomains use HTTPS before enabling
HSTS for subdomains or preload. Run `manage.py check --deploy` with the actual
hosting environment. Local HTTP development intentionally uses different settings.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

Tests cover authentication, permissions, bookings, payment verification, templates
and static-file references. External payment and email calls use test substitutes.
The same `requirements.txt` is sufficient to run the application and its tests.

## Repository notes

Commit application code, migrations, tests, static assets and `.env.example`.
Local databases, uploads, private proofs, environments and `.env` are ignored.
Run Git commands from this directory. No demo account passwords are bundled.

Before upgrading existing data, stop writes and back up `db.sqlite3`, `media/`
and `private_media/` together. Use SQLite's backup API for an open database.
Test migrations on a restored copy before applying them to the intended database;
keep all historical migrations. To roll back, restore matching code, database and
uploads, and reconcile payment activity since the backup before reopening.

Keep `DJANGO_TIME_ZONE` stable: existing bookings use `Asia/Kolkata`. Older paid
bookings with missing workspace/time information need verified records before
repair; never guess their slot or refund status. Ambiguous old chat messages are
preserved until their participants can be verified.

Test Razorpay capture/refund and email delivery before public use. For uncertain
payments, `manage.py reconcile_payments BOOKING_ID` reads the provider status and
updates verified captures or completed refunds; it does not charge or issue a
refund. Keep private proofs outside the public web root and schedule expired-session
cleanup with `manage.py clearsessions`.
