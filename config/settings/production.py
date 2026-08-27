from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

if SECRET_KEY == "development-only-insecure-secret-key":
    raise ImproperlyConfigured("Set a secure SECRET_KEY in the production environment.")

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS to the production domain; do not use *.")

if DATABASE_ENGINE != "postgresql":
    raise ImproperlyConfigured("Production must use PostgreSQL (DB_ENGINE=postgresql).")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("Set CSRF_TRUSTED_ORIGINS for the production HTTPS origin.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

