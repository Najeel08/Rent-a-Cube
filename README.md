# Rent-a-Cube

Rent-a-Cube is a Django 5.2 marketplace for discovering and booking flexible coworking spaces. It has separate user, owner, administrator, and technician portals.

## Features

- User registration, workspace search, cart, booking, payments, requests, and owner chat.
- Owner approval, workspace listing management, booking confirmation, technician assignment, and refunds.
- Custom administrator portal for owner approval and platform reporting.
- Technician portal for accepting or rejecting assigned service requests.
- Razorpay order creation, signature verification, and refunds.
- Public support inquiries stored for administrator triage in Django admin.

## Project layout

The Django project is nested in `workspace/`:

```text
workspace/
  manage.py
  workspace/       Django settings and URL configuration
  homeapp/         Public landing and contact pages
  user/            Customer portal
  owners/          Workspace-owner portal
  workadmin/       Custom administrator portal
  technician/      Technician portal
  Template/        Django templates
  static/          CSS, JavaScript, fonts, and images
  media/           Development uploads
```

## Local setup

Use Python 3.11 or later.

```powershell
cd workspace
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

`workspace/.env` is ignored by Git and provides the local development settings.
For another workstation, copy `workspace/.env.example` to `workspace/.env` and
replace the example secret with a generated value.

## Configuration

Set these environment variables before using external services or deploying:

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
RAZORPAY_API_KEY
RAZORPAY_API_SECRET_KEY
EMAIL_HOST
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_BACKEND
```

Without email credentials, Django uses its console email backend. Razorpay checkout and refunds require both Razorpay credentials.

## Verification

```powershell
cd workspace
python manage.py check
python manage.py test
```

## Notes

- `db.sqlite3` and `media/` are local development data and should not be committed.
- Owner proof documents are stored in `private_media/` and are available only through the custom admin portal.
- `DJANGO_DEBUG` defaults to `False`; set it explicitly for local development.
- The bundled virtual environments are local tooling, not source code.
- Production deployment requires secure environment variables, HTTPS, private document storage, and a production database.
