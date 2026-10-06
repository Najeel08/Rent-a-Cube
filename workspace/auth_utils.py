"""Shared authentication helpers used by all apps (user, owner, admin, technician)."""
import re
from django.contrib import messages
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.shortcuts import redirect
from django.utils.crypto import constant_time_compare

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def is_valid_email(email_str):
    """Standard, RFC-compliant email validator checking regex format and domain structure."""
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
    if name is not None:
        request.session['Name'] = name


def require_role(request, role, login_url):
    """Return a redirect if user doesn't have the required role, or None to proceed."""
    if request.session.get('role') != role or not request.session.get('id'):
        messages.info(request, 'Please login first')
        return redirect(login_url)
    return None


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
    """Check password against stored value. Supports both hashed and legacy plaintext passwords."""
    if not raw_password or not stored_password:
        return False
    if password_is_hashed(stored_password):
        return check_password(raw_password, stored_password)
    return constant_time_compare(str(raw_password), str(stored_password))


def upgrade_password_if_needed(obj, field_name, raw_password):
    """If stored password is plaintext, re-hash it so future logins use secure hashing."""
    current = getattr(obj, field_name)
    if raw_password and not password_is_hashed(current):
        setattr(obj, field_name, hash_password(raw_password))
        obj.save(update_fields=[field_name])
