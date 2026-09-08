from urllib.parse import parse_qs, unquote, urlparse


def config_from_url(url, *, conn_max_age=60):
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must be a postgres URL.")
    sslmode = (parse_qs(parsed.query).get("sslmode") or [""])[0]
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or "5432"),
        "CONN_MAX_AGE": int(conn_max_age),
    }
    if sslmode:
        config["OPTIONS"] = {"sslmode": sslmode}
    return config
