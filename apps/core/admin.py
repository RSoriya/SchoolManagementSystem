from django.contrib import admin

from .models import NumberSequence, PaymentMethod, SchoolSettings


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    list_display = ("school_name", "phone", "reminder_days_before_due")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "requires_reference", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")


@admin.register(NumberSequence)
class NumberSequenceAdmin(admin.ModelAdmin):
    list_display = ("key", "year", "last_value")
    readonly_fields = ("key", "year", "last_value")
