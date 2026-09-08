from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

if SECRET_KEY == "development-only-insecure-secret-key":
    raise ImproperlyConfigured("Set a secure SECRET_KEY in the production environment.")

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS to the production domain; do not use *.")

if DATABASE_ENGINE != "postgresql":
    raise ImproperlyConfigured("Production must use PostgreSQL (DB_ENGINE=postgresql or DATABASE_URL).")

DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"].setdefault("sslmode", env("DB_SSLMODE", "require"))

SPACES_KEY = env("SPACES_KEY", "")
SPACES_SECRET = env("SPACES_SECRET", "")
SPACES_BUCKET = env("SPACES_BUCKET", "")
SPACES_REGION = env("SPACES_REGION", "")
SPACES_ENDPOINT = env("SPACES_ENDPOINT", "")
SPACES_MEDIA_LOCATION = env("SPACES_MEDIA_LOCATION", "media")
SPACES_BACKUP_PREFIX = env("SPACES_BACKUP_PREFIX", "backups").strip("/")
ALLOW_FILESYSTEM_MEDIA = env_bool("ALLOW_FILESYSTEM_MEDIA", False)

if all([SPACES_KEY, SPACES_SECRET, SPACES_BUCKET, SPACES_REGION, SPACES_ENDPOINT]):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": SPACES_KEY,
            "secret_key": SPACES_SECRET,
            "bucket_name": SPACES_BUCKET,
            "endpoint_url": SPACES_ENDPOINT,
            "region_name": SPACES_REGION,
            "default_acl": "private",
            "querystring_auth": True,
            "querystring_expire": 3600,
            "file_overwrite": False,
            "location": SPACES_MEDIA_LOCATION,
            "addressing_style": "virtual",
            "signature_version": "s3v4",
        },
    }
elif not ALLOW_FILESYSTEM_MEDIA:
    raise ImproperlyConfigured(
        "Set SPACES_KEY, SPACES_SECRET, SPACES_BUCKET, SPACES_REGION, and SPACES_ENDPOINT."
    )

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("Set CSRF_TRUSTED_ORIGINS for the production HTTPS origin.")

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

