from django.contrib import admin

from .models import Payment, Receipt, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "course_class", "total_amount", "currency", "paid_on", "status")
    list_filter = ("status", "currency", "method")
    search_fields = ("student__student_id", "student__name_kh", "receipt__receipt_number")
    date_hierarchy = "paid_on"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "student_name_kh", "class_name", "status", "issued_at")
    list_filter = ("status",)
    search_fields = ("receipt_number", "student_id_snapshot", "student_name_kh")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "amount", "currency", "refunded_on", "method")
    list_filter = ("currency", "method")
    search_fields = ("payment__receipt__receipt_number", "payment__student__student_id", "reason")
    date_hierarchy = "refunded_on"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
