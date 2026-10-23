"""Django settings for Rent-a-Cube project."""
from pathlib import Path
from ipaddress import ip_network
import os
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_env(path):
    """Load simple KEY=VALUE pairs without overriding deployed environment values."""
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.isidentifier():
            os.environ.setdefault(key, value)


if os.environ.get('DJANGO_LOAD_ENV', '1') != '0':
    load_local_env(BASE_DIR / '.env')

TRUE_VALUES = ('1', 'true', 'yes', 'on')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in TRUE_VALUES


def env_int(name, default):
    try:
        return max(0, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


DEBUG = env_bool('DJANGO_DEBUG')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is False.')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'home.apps.HomeConfig',
    'owners',
    'admin_portal.apps.AdminPortalConfig',
    'accounts.apps.AccountsConfig',
    'technicians.apps.TechniciansConfig',
]

MIDDLEWARE = [
    'config.middleware.TrustedProxyMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'config.middleware.PortalSecurityMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
        # SQLite has no row locks. Acquire the writer lock before reading state
        # in atomic booking/refund transactions, including across worker processes.
        'OPTIONS': {'transaction_mode': 'IMMEDIATE', 'timeout': 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'Asia/Kolkata')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
PRIVATE_MEDIA_ROOT = os.environ.get('DJANGO_PRIVATE_MEDIA_ROOT', os.path.join(BASE_DIR, 'private_media'))

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SECURE_PROXY_SSL_HEADER = (
    ('HTTP_X_FORWARDED_PROTO', 'https')
    if env_bool('DJANGO_USE_X_FORWARDED_PROTO')
    else None
)
TRUSTED_PROXY_IPS = [
    value.strip() for value in os.environ.get('DJANGO_TRUSTED_PROXY_IPS', '').split(',')
    if value.strip()
]
try:
    for proxy in TRUSTED_PROXY_IPS:
        if ip_network(proxy, strict=False).prefixlen == 0:
            raise ValueError('Trusting every address is not allowed.')
except ValueError as exc:
    raise ImproperlyConfigured('DJANGO_TRUSTED_PROXY_IPS must contain valid IP addresses or CIDR networks.') from exc
if SECURE_PROXY_SSL_HEADER and not TRUSTED_PROXY_IPS:
    raise ImproperlyConfigured('Set DJANGO_TRUSTED_PROXY_IPS before trusting forwarded HTTPS headers.')
SECURE_HSTS_SECONDS = env_int('DJANGO_SECURE_HSTS_SECONDS', 31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG
)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', not DEBUG)
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

RAZORPAY_API_KEY = os.environ.get('RAZORPAY_API_KEY', '')
RAZORPAY_API_SECRET_KEY = os.environ.get('RAZORPAY_API_SECRET_KEY', '')
ALLOW_DEMO_PAYMENTS = DEBUG and env_bool('ALLOW_DEMO_PAYMENTS')
BOOKING_HOLD_MINUTES = 15
SESSION_COOKIE_AGE = 60 * 60 * 12
ADMIN_IDLE_TIMEOUT = 15 * 60
TECHNICIAN_IDLE_TIMEOUT = 30 * 60
PRIVILEGED_SESSION_MAX_AGE = 8 * 60 * 60
# Enable after exercising the provider's sandbox checkout with this policy.
CHECKOUT_CSP_ENFORCE = env_bool('DJANGO_CHECKOUT_CSP_ENFORCE')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
DATA_UPLOAD_MAX_NUMBER_FILES = 4
EMAIL_TIMEOUT = 10

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else 'config.security.RedactedConsoleEmailBackend',
)
if EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
    EMAIL_BACKEND = 'config.security.RedactedConsoleEmailBackend'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# Fail closed if local HTTP settings accidentally accompany a production launch.
if not DEBUG:
    if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith(('django-insecure-', 'replace-')):
        raise ImproperlyConfigured('Production requires a strong DJANGO_SECRET_KEY of at least 50 characters.')
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured('Production requires explicit DJANGO_ALLOWED_HOSTS.')
    if not all((SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)):
        raise ImproperlyConfigured('Production requires HTTPS redirection and secure session/CSRF cookies. Do not load local HTTP settings.')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {'redact_setup_links': {'()': 'config.security.SetupLinkFilter'}},
    'formatters': {
        'safe': {'()': 'config.security.SafeFormatter', 'format': '{levelname} {message}', 'style': '{'},
        'server': {'()': 'config.security.SafeServerFormatter', 'format': '[{server_time}] {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'filters': ['redact_setup_links'], 'formatter': 'safe'},
        'django.server': {'class': 'logging.StreamHandler', 'filters': ['redact_setup_links'], 'formatter': 'server'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'django.server': {'handlers': ['django.server'], 'level': 'INFO', 'propagate': False},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
