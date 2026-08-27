from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.backup import create_backup, verify_backup


class Command(BaseCommand):
    help = "Create a database backup and keep the last 30 days."

    def add_arguments(self, parser):
        parser.add_argument("--verify", action="store_true", help="Verify the new backup after writing it.")

    def handle(self, *args, **options):
        try:
            path = create_backup()
            if options["verify"]:
                verify_backup(path)
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise CommandError(message) from exc
        log_event(
            action=AuditEvent.Action.BACKUP_CREATED,
            summary=f"បម្រុងទុកទិន្នន័យ · {path.name}",
            extra={"path": str(path)},
        )
        self.stdout.write(self.style.SUCCESS(str(path)))
