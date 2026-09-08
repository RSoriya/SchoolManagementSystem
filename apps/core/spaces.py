from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def spaces_configured():
    return bool(
        getattr(settings, "SPACES_BUCKET", "")
        and getattr(settings, "SPACES_KEY", "")
        and getattr(settings, "SPACES_SECRET", "")
        and getattr(settings, "SPACES_ENDPOINT", "")
        and getattr(settings, "SPACES_REGION", "")
    )


def backup_prefix():
    return getattr(settings, "SPACES_BACKUP_PREFIX", "backups").strip("/")


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        region_name=settings.SPACES_REGION,
        endpoint_url=settings.SPACES_ENDPOINT,
        aws_access_key_id=settings.SPACES_KEY,
        aws_secret_access_key=settings.SPACES_SECRET,
        config=Config(s3={"addressing_style": "virtual"}, signature_version="s3v4"),
    )


def backup_key(name):
    return f"{backup_prefix()}/{name}"


def upload_backup(path):
    if not spaces_configured():
        return
    _client().upload_file(str(path), settings.SPACES_BUCKET, backup_key(path.name))


def download_backup(name, destination):
    if not spaces_configured():
        raise ValidationError("Spaces មិនទាន់កំណត់។")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _client().download_file(settings.SPACES_BUCKET, backup_key(name), str(destination))
    return destination


def list_remote_backups():
    if not spaces_configured():
        return []
    prefix = f"{backup_prefix()}/"
    response = _client().list_objects_v2(Bucket=settings.SPACES_BUCKET, Prefix=prefix)
    records = []
    for item in response.get("Contents") or []:
        name = item["Key"][len(prefix) :]
        if "/" in name or not name:
            continue
        suffix = name.rsplit(".", 1)[-1]
        if suffix not in {"dump", "sqlite3", "sql"}:
            continue
        modified = item["LastModified"]
        if timezone.is_naive(modified):
            modified = timezone.make_aware(modified, dt_timezone.utc)
        records.append(
            {
                "name": name,
                "modified": timezone.localtime(modified),
                "size_kb": max(1, int(item.get("Size") or 0) // 1024),
            }
        )
    records.sort(key=lambda item: item["modified"], reverse=True)
    return records


def prune_remote_backups():
    if not spaces_configured():
        return []
    keep = int(getattr(settings, "BACKUP_KEEP_DAYS", 30))
    cutoff = timezone.now() - timedelta(days=keep)
    removed = []
    client = _client()
    for record in list_remote_backups():
        modified = record["modified"]
        if timezone.is_naive(modified):
            modified = timezone.make_aware(modified, dt_timezone.utc)
        if modified >= cutoff:
            continue
        client.delete_object(Bucket=settings.SPACES_BUCKET, Key=backup_key(record["name"]))
        removed.append(record["name"])
    return removed
