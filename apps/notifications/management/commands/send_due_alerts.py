from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.notifications.services import send_due_alerts


class Command(BaseCommand):
    help = "Send due-soon and overdue Telegram alerts to the admin chat."

    def handle(self, *args, **options):
        try:
            result = send_due_alerts()
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise CommandError(message) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"sent={result['sent']} failed={result['failed']} skipped={result['skipped']}"
            )
        )
