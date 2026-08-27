import socket

from .base import *

DEBUG = env_bool("DEBUG", True)


def _lan_http_origins(port="8000"):
    origins = {
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
    }
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            origins.add(f"http://{sock.getsockname()[0]}:{port}")
    except OSError:
        pass
    try:
        origins.add(f"http://{socket.gethostbyname(socket.gethostname())}:{port}")
    except OSError:
        pass
    return sorted(origins)


if DEBUG:
    # Let phones/iPads on the same Wi-Fi open the local server by LAN IP.
    ALLOWED_HOSTS = ["*"]
    CSRF_TRUSTED_ORIGINS = _lan_http_origins()
    # Safari on iPad mismatches the CSRF cookie when the site is opened by IP.
    CSRF_USE_SESSIONS = True

STORAGES["staticfiles"] = {
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}

