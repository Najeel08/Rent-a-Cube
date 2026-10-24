# Rent-a-Cube

Rent-a-Cube is a web application developed using Django that allows users to find and book coworking spaces. It provides separate portals for customers, workspace owners, technicians, and platform administrators.

## Features

- **Customers:** Browse workspaces, make bookings, manage payments, message owners, and request services.
- **Workspace Owners:** Manage workspaces, bookings, refunds, and technician assignments.
- **Technicians:** View and respond to assigned service requests.
- **Platform Administrators:** Approve workspace owners and manage platform activities.

## Technologies Used

- Python
- Django
- SQLite
- HTML, CSS, and JavaScript
- Razorpay for online payments

## Project Structure

```text
Rent-a-Cube/
├── config/          # Project settings and URL configuration
├── home/            # Homepage and support
├── accounts/        # Customer accounts and bookings
├── owners/          # Workspace owner portal
├── technicians/     # Technician portal
├── admin_portal/    # Platform administration
├── templates/       # HTML templates
├── static/          # CSS, JavaScript, and images
├── manage.py        # Django management commands
└── requirements.txt # Python dependencies
```

## Installation and Setup

### Prerequisites

- Python 3.13
- Git (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/Najeel08/Rent-a-Cube.git
cd Rent-a-Cube
```

If you already have the project files, open a terminal in the project directory instead.

### 2. Create a Virtual Environment

```powershell
py -3.13 -m venv .venv
```

### 3. Install Dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a local `.env` file using `.env.example` as a reference. Set the required Django secret key and other configuration values. Keep your `.env` file private and never commit real credentials to GitHub.

### 5. Apply Database Migrations

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

### 6. Start the Development Server

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Open the application at http://127.0.0.1:8000/.

## User Accounts

The application supports four roles:

- **Customer:** Register through the website.
- **Workspace Owner:** Register and wait for administrator approval.
- **Technician:** Account created by an approved workspace owner.
- **Platform Administrator:** Account managed through the Django administration system.

To create a Django administrator account, run:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

## Running Tests

Run the following command to execute the project's automated tests:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

Each app keeps its tests in a `tests/` folder, grouped by feature. Shared test
accounts and workspaces are created by `accounts/tests/base.py`. Tests use
Django's separate test database rather than your development records.

To run only one app or one test file, use its Python module path:

```powershell
.\.venv\Scripts\python.exe manage.py test owners.tests
.\.venv\Scripts\python.exe manage.py test accounts.tests.test_payments
```

Before running the tests, you can also check the configuration and migration state:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

## Finding Your Way Around the Code

The two larger portals use a `views/` folder to keep related pages together:

- `accounts/views/`: `auth.py` for customer accounts, `workspaces.py` for browsing
  and reservations, `bookings.py` for the cart and checkout, and `support.py` for
  service requests and conversations.
- `owners/views/`: `auth.py` for owner accounts and profiles, `workspaces.py` for
  listings, `staff.py` for technicians and assignments, `bookings.py` for bookings
  and refunds, and `messaging.py` for conversations.

Each folder's `__init__.py` exposes the views used by `urls.py`. The smaller
portals still use a single `views.py` file. Existing URLs have not changed.

Shared customer-owner message creation is in `accounts/messaging.py`. Reservation
conflicts and payment recording remain in `accounts/reservations.py` and
`accounts/payments.py`. Role and session checks stay in `config/auth_utils.py`.

Models and migrations stay in their original apps. Some app labels and database
table names retain older names to keep existing databases compatible; do not
rename them or remove old migrations as a cleanup step.

## Security Notes

- Keep secret keys, passwords, and API credentials private.
- Use test-mode payment credentials during development.
- Do not commit local databases, private documents, or environment files.
- Configure HTTPS and production security settings before deploying the application.

## Project Status

Rent-a-Cube is a student-developed project demonstrating workspace booking, role-based access, payment integration, and service management using Django.
