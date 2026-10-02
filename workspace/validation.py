from datetime import date, datetime
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_BOOKING_DURATION_HOURS = 72
MAX_HOURLY_PRICE = 1_000_000


def validate_image_upload(upload, field_label):
    """Validate an uploaded raster image without trusting its filename or MIME type."""
    if upload is None:
        raise ValidationError(f'{field_label} is required.')
    if upload.size > MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError(f'{field_label} must be 5 MB or smaller.')
    if Path(upload.name).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f'{field_label} must be a JPG, PNG, or WebP image.')
    try:
        image = Image.open(upload)
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(f'{field_label} is not a valid image file.') from exc
    finally:
        upload.seek(0)


def required_text(data, field_name, label, max_length=None):
    """Return a required trimmed field or a user-facing validation error."""
    value = str(data.get(field_name, '')).strip()
    if not value:
        raise ValidationError(f'{label} is required.')
    if max_length and len(value) > max_length:
        raise ValidationError(f'{label} must be {max_length} characters or fewer.')
    return value


def positive_integer(value, label, maximum=None):
    """Parse a positive integer while keeping validation feedback consistent."""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f'{label} must be a whole number.') from exc
    if number <= 0:
        raise ValidationError(f'{label} must be greater than zero.')
    if maximum is not None and number > maximum:
        raise ValidationError(f'{label} must be {maximum} or less.')
    return number


def validate_booking_date(value):
    """Accept future and current ISO calendar dates only."""
    try:
        booking_date = datetime.strptime(str(value or ''), '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValidationError('Enter a valid booking date.') from exc
    if booking_date < date.today():
        raise ValidationError('Booking date cannot be in the past.')
    return booking_date.isoformat()


def validate_booking_start_time(value):
    """Accept a valid 24-hour booking start time."""
    try:
        return datetime.strptime(str(value or ''), '%H:%M').time()
    except ValueError as exc:
        raise ValidationError('Enter a valid booking start time.') from exc


def validate_phone_number(value):
    """Accept a practical international phone-number length without coercing it to an integer."""
    phone = str(value or '').strip()
    if not phone.isdigit() or not 7 <= len(phone) <= 15:
        raise ValidationError('Enter a valid phone number using 7 to 15 digits.')
    return phone
