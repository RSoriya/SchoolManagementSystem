from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_roles_on_migrate(**kwargs):
    from django.contrib.auth.models import Permission

    if not Permission.objects.filter(codename="collect_payment").exists():
        return
    from .roles import sync_role_groups

    sync_role_groups()


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        post_migrate.connect(sync_roles_on_migrate, dispatch_uid="school_sync_role_groups")
