"""Shared authentication helpers used by all apps (user, owner, admin, technician)."""
import re
from django.contrib import messages
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.shortcuts import redirect
from django.utils.crypto import constant_time_compare, salted_hmac
from django.middleware.csrf import rotate_token

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def is_valid_email(email_str):
    """Validate the email format accepted by the registration forms."""
    if not email_str or not isinstance(email_str, str):
        return False
    clean_email = email_str.strip()
    if not EMAIL_REGEX.match(clean_email):
        return False
    try:
        django_validate_email(clean_email)
        return True
    except ValidationError:
        return False


def normalize_email(email_str):
    """Normalize email to lowercase and trimmed."""
    if not email_str:
        return ""
    return str(email_str).strip().lower()


def login_role(request, role, obj, name=None):
    """Set session for a logged-in user. Flushes first to prevent session fixation."""
    request.session.flush()
    request.session['role'] = role
    request.session['id'] = obj.id
    request.session['auth_hash'] = session_auth_hash(obj)
    rotate_token(request)
    if name is not None:
        request.session['Name'] = name


def require_role(request, role, login_url):
    """Return a redirect if user doesn't have the required role, or None to proceed."""
    if request.session.get('role') != role or not request.session.get('id'):
        messages.info(request, 'Please login first')
        return redirect(login_url)
    model_names = {'user': ('user', 'Customer'), 'owner': ('owners', 'Owner'),
                   'technician': ('owners', 'Technician'), 'admin': ('workadmin', 'PlatformAdmin')}
    accounts = apps.get_model(*model_names[role]).objects.all()
    if role == 'technician':
        accounts = accounts.select_related('owner')
    obj = accounts.filter(pk=request.session['id']).first()
    approved = obj is not None
    if approved and role == 'owner':
        approved = obj.accept and not obj.reject
    if approved and role == 'technician':
        approved = obj.owner.accept and not obj.owner.reject
    if not approved or not constant_time_compare(request.session.get('auth_hash', ''), session_auth_hash(obj)):
        request.session.flush()
        messages.info(request, 'Please sign in again. Your account access may have changed.')
        return redirect(login_url)
    return None


def session_auth_hash(obj):
    return salted_hmac('rentacube.session', obj.password).hexdigest() if obj else ''


def password_is_hashed(value):
    """Check if a password string is already hashed using Django's hasher."""
    try:
        identify_hasher(value)
        return True
    except ValueError:
        return False


def hash_password(raw_password):
    """Hash a plain text password using Django's default hasher."""
    return make_password(raw_password)


def password_matches(raw_password, stored_password):
    """Check credentials without giving missing accounts a faster failure path."""
    if not stored_password or not password_is_hashed(stored_password):
        # Match Django's authentication backend: burn the default hasher's work
        # even when an account is absent or has not set its password yet.
        make_password(raw_password or '')
        return False
    valid = check_password(raw_password or '', stored_password)
    return bool(raw_password) and valid


def upgrade_password_if_needed(obj, field_name, raw_password):
    """Upgrade supported older hashes after a successful password check."""
    def setter(password):
        setattr(obj, field_name, hash_password(password))
        obj.save(update_fields=[field_name])

    check_password(raw_password, getattr(obj, field_name), setter=setter)
