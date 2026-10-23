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

Python 3.13, Django 6.1, SQLite, HTML, CSS and JavaScript. Razorpay handles online
payments. Django handles templates, sessions, password hashing and email.

`requirements.txt` pins application packages and their dependencies. Pillow checks
uploaded images; Requests and Certifi support the Razorpay connection. The `tzdata`
package supplies time-zone information on Windows. No Node.js or separate test
dependencies are needed.

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

Install Python 3.13; Git is useful for cloning and updating the repository. Open
PowerShell in the `Rent-a-Cube` directory containing `manage.py`.

For a new installation:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

On first setup only, generate a secret key:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Replace the placeholder value of `DJANGO_SECRET_KEY` in `.env` with the generated
key. Keep that key stable. For an existing installation, keep the existing `.env`
and secret key; do not generate a replacement during a dependency update.

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
For another port, use `.\.venv\Scripts\python.exe manage.py runserver 8001`.

### Update an existing installation

Stop the server and back up existing data first (see Repository notes). Keep the
existing environment and `.env`, then install the pinned versions and run the
checks before starting the server again:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The Django 6.1 upgrade keeps the existing application models and migrations.
Existing email settings and session helpers still work, but Django reports
deprecation warnings for them. They need code changes before a future upgrade to
Django 2028; do not suppress the warnings or upgrade Django independently of
`requirements.txt`.

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

For email delivery, add `EMAIL_HOST`, `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`
to your private `.env` or hosting environment. The current SMTP configuration uses
STARTTLS on port 587. With both credentials set, Django selects SMTP automatically
unless `EMAIL_BACKEND` is explicitly overridden. Without them, it uses the console
backend; that backend prints emails locally and does not deliver them.

For real payments, configure `RAZORPAY_API_KEY` and `RAZORPAY_API_SECRET_KEY` in
`.env`. Use Razorpay test-mode keys for local integration testing. For local
demonstration only, `ALLOW_DEMO_PAYMENTS=True` works when `DJANGO_DEBUG=True`;
it does not charge money. Without keys or explicit demo mode, checkout remains
disabled. Demo mode is always disabled in production.

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

Use a production WSGI or ASGI server and HTTPS; Django's `runserver` is for local
development. Choose and install a server suited to your hosting platform; one is
not included in `requirements.txt`. Collect static files with the production
environment configured:

```powershell
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check --deploy
```

Configure your web server or hosting service to serve `staticfiles/` and public
`media/`. Keep `private_media/` inaccessible to direct public requests. SQLite
and uploads need persistent storage on the hosting service.

If HTTPS ends at a trusted reverse proxy, configure it to strip untrusted
forwarded headers before enabling `DJANGO_USE_X_FORWARDED_PROTO`. Verify all
subdomains use HTTPS before enabling
HSTS for subdomains or preload. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the exact
trusted origins, including `https://`, if your deployment needs cross-origin form
submissions. Run the deployment check with the actual hosting environment. Local
HTTP development intentionally uses different settings.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

Tests cover authentication, permissions, bookings, payment verification, templates
and static-file references. External payment and email calls use test substitutes.
The same `requirements.txt` is sufficient to run the application and its tests.
Tests create a separate disposable database. They do not verify live Razorpay or
SMTP delivery. If `migrate --check` reports pending migrations, review the plan and
apply them with `migrate`; do not delete the database or migration files.

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
payments, use the command below, replacing `BOOKING_ID` with the existing booking's
numeric ID. It reads the provider status and updates verified captures or completed
refunds; it does not charge or issue a refund.

```powershell
.\.venv\Scripts\python.exe manage.py reconcile_payments BOOKING_ID
```

Keep private proofs outside the public web root. Schedule expired-session cleanup
with `.\.venv\Scripts\python.exe manage.py clearsessions`.
