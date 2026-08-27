from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.core.backup import list_backups, verify_backup


class Command(BaseCommand):
    help = "Verify a backup file, or the newest backup if none is given."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="")

    def handle(self, *args, **options):
        path = options["path"]
        if not path:
            backups = list_backups()
            if not backups:
                raise CommandError("មិនទាន់មានឯកសារបម្រុងទុក។")
            path = backups[0]
        try:
            result = verify_backup(path)
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise CommandError(message) from exc
        self.stdout.write(self.style.SUCCESS(f"{path}: {result}"))
