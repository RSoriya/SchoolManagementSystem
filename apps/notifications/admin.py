from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("sent_on", "kind", "status", "enrollment", "channel")
    list_filter = ("kind", "status")
    search_fields = ("message", "error", "enrollment__student__name_kh")
    date_hierarchy = "sent_on"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
