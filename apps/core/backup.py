import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def backup_dir():
    path = Path(settings.BACKUP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def keep_days():
    return int(getattr(settings, "BACKUP_KEEP_DAYS", 30))


def list_backups():
    files = [
        path
        for path in backup_dir().iterdir()
        if path.is_file() and path.suffix in {".dump", ".sqlite3", ".sql"}
    ]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return files


def backup_records(limit=8):
    records = []
    for path in list_backups()[:limit]:
        records.append(
            {
                "name": path.name,
                "modified": datetime.fromtimestamp(path.stat().st_mtime),
                "size_kb": max(1, path.stat().st_size // 1024),
            }
        )
    return records


def prune_backups():
    cutoff = timezone.now() - timedelta(days=keep_days())
    removed = []
    for path in list_backups():
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=dt_timezone.utc)
        if modified < cutoff:
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed


def _timestamp():
    return timezone.localtime().strftime("%Y-%m-%d_%H%M%S")


def _pg_env():
    db = settings.DATABASES["default"]
    env = os.environ.copy()
    if db.get("PASSWORD"):
        env["PGPASSWORD"] = str(db["PASSWORD"])
    return env


def _find_tool(name):
    found = shutil.which(name) or shutil.which(f"{name}.exe")
    if found:
        return found
    candidates = []
    pg_root = Path(r"C:\Program Files\PostgreSQL")
    if pg_root.exists():
        candidates.extend(pg_root.glob(f"*/bin/{name}.exe"))
    candidates.extend([Path(f"/usr/bin/{name}"), Path(f"/usr/local/bin/{name}")])
    for candidate in sorted(candidates, reverse=True):
        if candidate.exists():
            return str(candidate)
    raise ValidationError(f"រកមិនឃើញ {name}។ សូមដំឡើង PostgreSQL client tools។")


def create_backup():
    stamp = _timestamp()
    db = settings.DATABASES["default"]
    engine = db["ENGINE"]
    if "postgresql" in engine:
        destination = backup_dir() / f"school_{stamp}.dump"
        command = [
            _find_tool("pg_dump"),
            "--format=custom",
            "--file",
            str(destination),
            "--dbname",
            db["NAME"],
            "--host",
            db.get("HOST") or "127.0.0.1",
            "--port",
            str(db.get("PORT") or "5432"),
            "--username",
            db.get("USER") or "postgres",
        ]
        completed = subprocess.run(command, env=_pg_env(), capture_output=True, text=True)
        if completed.returncode != 0:
            destination.unlink(missing_ok=True)
            raise ValidationError(completed.stderr.strip() or "pg_dump បរាជ័យ។")
    elif "sqlite" in engine:
        destination = backup_dir() / f"school_{stamp}.sqlite3"
        shutil.copy2(db["NAME"], destination)
    else:
        raise ValidationError("ម៉ាស៊ីនទិន្នន័យនេះមិនគាំទ្រការបម្រុងទុកទេ។")
    prune_backups()
    return destination


def verify_backup(path):
    path = Path(path)
    if not path.exists():
        raise ValidationError("រកមិនឃើញឯកសារបម្រុងទុក។")
    if path.suffix == ".sqlite3":
        connection = sqlite3.connect(path)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
        if not result or result[0] != "ok":
            raise ValidationError("SQLite backup មិនត្រឹមត្រូវ។")
        return "sqlite integrity_check=ok"
    if path.suffix == ".dump":
        command = [_find_tool("pg_restore"), "--list", str(path)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ValidationError(completed.stderr.strip() or "pg_restore --list បរាជ័យ។")
        return "pg_restore --list ok"
    raise ValidationError("ប្រភេទឯកសារបម្រុងទុកមិនស្គាល់។")


def restore_backup(path, *, yes=False):
    if not yes:
        raise ValidationError("សូមបញ្ជាក់ --yes មុនពេល restore។")
    path = Path(path)
    verify_backup(path)
    db = settings.DATABASES["default"]
    if "sqlite" in db["ENGINE"]:
        shutil.copy2(path, db["NAME"])
        return path
    if "postgresql" not in db["ENGINE"]:
        raise ValidationError("ម៉ាស៊ីនទិន្នន័យនេះមិនគាំទ្រ restore ទេ។")
    command = [
        _find_tool("pg_restore"),
        "--clean",
        "--if-exists",
        "--no-owner",
        "--dbname",
        db["NAME"],
        "--host",
        db.get("HOST") or "127.0.0.1",
        "--port",
        str(db.get("PORT") or "5432"),
        "--username",
        db.get("USER") or "postgres",
        str(path),
    ]
    completed = subprocess.run(command, env=_pg_env(), capture_output=True, text=True)
    if completed.returncode != 0:
        raise ValidationError(completed.stderr.strip() or "pg_restore បរាជ័យ។")
    return path
