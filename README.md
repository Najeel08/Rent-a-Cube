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

## Security Notes

- Keep secret keys, passwords, and API credentials private.
- Use test-mode payment credentials during development.
- Do not commit local databases, private documents, or environment files.
- Configure HTTPS and production security settings before deploying the application.

## Project Status

Rent-a-Cube is a student-developed project demonstrating workspace booking, role-based access, payment integration, and service management using Django.