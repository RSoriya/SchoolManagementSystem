from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.core.backup import restore_backup, verify_backup


class Command(BaseCommand):
    help = "Restore a backup file. Requires --yes. Stop the app first."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--yes", action="store_true", help="Confirm this destructive restore.")

    def handle(self, *args, **options):
        try:
            verify_backup(options["path"])
            restore_backup(options["path"], yes=options["yes"])
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise CommandError(message) from exc
        self.stdout.write(self.style.SUCCESS(f"restored {options['path']}"))
