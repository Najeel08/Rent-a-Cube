"""Customer registration, sign-in and dashboard views."""
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render

from config.auth_utils import (
    hash_password,
    is_valid_email,
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)
from config.validation import (
    required_text,
    validate_image_upload,
    validate_phone_number,
)

from ..models import Customer


def _user_guard(request):
    """Check if user is logged in, redirect to login page if not."""
    return require_role(request, 'user', 'login')


def register(request):
    """Handle user registration - validate input and create new user."""
    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=50))
            phone = validate_phone_number(request.POST.get('phone'))
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            password = required_text(request.POST, 'password', 'Password')
            confirm_password = required_text(request.POST, 'cpassword', 'Password confirmation')
            validate_password(password, Customer(name=name, email=email))
            image = request.FILES.get('image')
            validate_image_upload(image, 'Profile image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'accounts/register.html')

        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. alex@company.com)")
            return render(request, 'accounts/register.html')

        if password != confirm_password:
            messages.info(request, 'password not match')
            return render(request, 'accounts/register.html')

        if Customer.objects.filter(email__iexact=email).exists():
            messages.info(request, "email already exists")
        elif Customer.objects.filter(name=name).exists():
            messages.info(request, "user already exists")
        else:
            try:
                with transaction.atomic():
                    Customer.objects.create(
                        name=name,
                        email=email,
                        phone_number=phone,
                        place=place,
                        password=hash_password(password),
                        image=image,
                    )
            except IntegrityError:
                messages.error(request, 'This email address is already registered.')
                return render(request, 'accounts/register.html')
            messages.info(request, "Registration successful. Please login.")
            return redirect('login')

    return render(request, 'accounts/register.html')


def sign_in(request):
    """Handle user login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        user = Customer.objects.filter(email__iexact=email).first()

        if password_matches(password, user.password if user else None) and user:
            upgrade_password_if_needed(user, 'password', password)
            login_role(request, 'user', user, user.name)
            return redirect('dashboard')
        messages.info(request, 'Invalid User')

    return render(request, 'accounts/login.html')


def dashboard(request):
    """Display user home/dashboard page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return render(request, 'accounts/dashboard.html')
