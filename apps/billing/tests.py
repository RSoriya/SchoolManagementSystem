from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Course, CourseClass, Enrollment
from apps.academics.services import enroll_student
from apps.audit.models import AuditEvent
from apps.billing.models import Payment, Receipt, Refund
from apps.billing.services import collect_payment, refund_payment, revenue_on, void_payment
from apps.core.models import PaymentMethod
from apps.students.models import Student


class BillingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
            full_name_kh="អ្នកគ្រប់គ្រង",
        )
        self.client.force_login(self.user)
        self.course = Course.objects.create(
            name="English Level 1",
            fee_type=Course.FeeType.MONTHLY,
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        self.course_class = CourseClass.objects.create(
            course=self.course,
            name="English Level 1 – Morning",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
            start_time=time(8, 0),
            end_time=time(9, 30),
        )
        self.student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender=Student.Gender.MALE,
            phone="012345678",
        )
        self.enrollment = enroll_student(
            self.student,
            self.course_class,
            user=self.user,
            next_due_date=date(2026, 8, 1),
        )
        self.cash = PaymentMethod.objects.get(code="cash")
        self.aba = PaymentMethod.objects.get(code="aba")

    def _pay(self, **overrides):
        today = timezone.localdate()
        payload = {
            "enrollment": self.enrollment,
            "paid_on": today,
            "tuition_amount": Decimal("30.00"),
            "method": self.cash,
            "period_label": "សីហា 2026",
            "next_due_date": today + timedelta(days=30),
            "user": self.user,
        }
        payload.update(overrides)
        return collect_payment(**payload)

    def test_collect_payment_assigns_receipt_number(self):
        payment = self._pay()
        year = timezone.localdate().year
        self.assertEqual(payment.receipt.receipt_number, f"RCP-{year}-000001")
        self.assertEqual(payment.total_amount, Decimal("30.00"))
        self.assertEqual(payment.currency, "USD")
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.previous_due_date, date(2026, 8, 1))
        self.assertEqual(self.enrollment.next_due_date, payment.next_due_date)

    def test_cash_does_not_need_reference(self):
        payment = self._pay(method=self.cash, transaction_reference="")
        self.assertEqual(payment.transaction_reference, "")

    def test_aba_requires_reference(self):
        with self.assertRaises(ValidationError):
            self._pay(method=self.aba, transaction_reference="")

    def test_discount_reduces_total(self):
        payment = self._pay(discount_amount=Decimal("5.00"), scholarship_amount=Decimal("5.00"))
        self.assertEqual(payment.total_amount, Decimal("20.00"))

    def test_zero_total_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._pay(tuition_amount=Decimal("10.00"), discount_amount=Decimal("10.00"))

    def test_monthly_auto_sets_next_due_date(self):
        payment = self._pay(next_due_date=None)
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.next_due_date, date(2026, 9, 1))
        self.assertEqual(self.enrollment.next_due_date, date(2026, 9, 1))
        self.assertEqual(payment.period_start, date(2026, 8, 1))
        self.assertEqual(payment.period_end, date(2026, 8, 31))

    def test_monthly_uses_paid_on_when_enrollment_has_no_due(self):
        self.enrollment.next_due_date = None
        self.enrollment.save(update_fields=["next_due_date", "updated_at"])
        payment = self._pay(
            paid_on=date(2026, 8, 15),
            next_due_date=None,
            period_start=None,
            period_end=None,
            period_label="",
        )
        self.assertEqual(payment.next_due_date, date(2026, 9, 15))
        self.assertEqual(payment.period_start, date(2026, 8, 1))
        self.assertEqual(payment.period_end, date(2026, 8, 31))
        self.assertEqual(payment.period_label, "សីហា 2026")

    def test_monthly_second_payment_advances_another_month(self):
        self._pay(next_due_date=None)
        payment = self._pay(next_due_date=None, period_start=None, period_end=None, period_label="")
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.period_start, date(2026, 9, 1))
        self.assertEqual(payment.period_end, date(2026, 9, 30))
        self.assertEqual(payment.next_due_date, date(2026, 10, 1))
        self.assertEqual(self.enrollment.next_due_date, date(2026, 10, 1))

    def test_monthly_manual_next_due_wins(self):
        chosen = date(2026, 10, 15)
        payment = self._pay(next_due_date=chosen)
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.next_due_date, chosen)
        self.assertEqual(self.enrollment.next_due_date, chosen)

    def test_add_calendar_month_clamps_month_end(self):
        from apps.billing.services import add_calendar_month

        self.assertEqual(add_calendar_month(date(2026, 1, 31)), date(2026, 2, 28))
        self.assertEqual(add_calendar_month(date(2026, 8, 1)), date(2026, 9, 1))

    def test_partial_payment_keeps_due_date_and_remaining(self):
        payment = self._pay(tuition_amount=Decimal("10.00"), next_due_date=None)
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.total_amount, Decimal("10.00"))
        self.assertEqual(payment.balance_after, Decimal("20.00"))
        self.assertTrue(payment.is_partial)
        self.assertEqual(self.enrollment.next_due_date, date(2026, 8, 1))
        self.assertEqual(payment.next_due_date, date(2026, 8, 1))

    def test_completing_partial_advances_monthly_due(self):
        self._pay(tuition_amount=Decimal("10.00"), next_due_date=None)
        payment = self._pay(tuition_amount=Decimal("20.00"), next_due_date=None)
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.balance_after, Decimal("0.00"))
        self.assertFalse(payment.is_partial)
        self.assertEqual(self.enrollment.next_due_date, date(2026, 9, 1))

    def test_cannot_pay_more_than_remaining(self):
        self._pay(tuition_amount=Decimal("10.00"), next_due_date=None)
        with self.assertRaises(ValidationError):
            self._pay(tuition_amount=Decimal("25.00"), next_due_date=None)

    def test_void_partial_restores_remaining(self):
        from apps.billing.services import period_balance

        payment = self._pay(tuition_amount=Decimal("10.00"), next_due_date=None)
        void_payment(payment, user=self.user, reason="បញ្ចូលខុស")
        balance = period_balance(self.enrollment)
        self.assertEqual(balance["remaining"], Decimal("30.00"))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.next_due_date, date(2026, 8, 1))

    def test_payment_form_payload_includes_remaining(self):
        self._pay(tuition_amount=Decimal("10.00"), next_due_date=None)
        response = self.client.get(reverse("billing:payment_list"))
        self.assertContains(response, '"remaining": "20.00"')
        self.assertContains(response, "នៅជំពាក់")

    def test_payment_and_receipt_cannot_be_deleted(self):
        payment = self._pay()
        receipt = payment.receipt
        with self.assertRaises(ValidationError):
            payment.delete()
        with self.assertRaises(ValidationError):
            receipt.delete()
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())
        self.assertTrue(Receipt.objects.filter(pk=receipt.pk).exists())

    def test_void_keeps_records_and_restores_due_date(self):
        original_due = self.enrollment.next_due_date
        payment = self._pay()
        void_payment(payment, user=self.user, reason="បញ្ចូលខុស")
        payment.refresh_from_db()
        receipt = payment.receipt
        receipt.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.VOIDED)
        self.assertEqual(receipt.status, Receipt.Status.VOIDED)
        self.assertEqual(self.enrollment.next_due_date, original_due)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())
        self.assertTrue(Receipt.objects.filter(pk=receipt.pk).exists())

    def test_cannot_void_twice(self):
        payment = self._pay()
        void_payment(payment, user=self.user)
        with self.assertRaises(ValidationError):
            void_payment(payment, user=self.user)

    def test_payment_create_view_issues_receipt(self):
        today = timezone.localdate()
        response = self.client.post(
            reverse("billing:payment_create"),
            {
                "enrollment": self.enrollment.pk,
                "paid_on": today.isoformat(),
                "tuition_amount": "30.00",
                "registration_fee": "0",
                "late_fee": "0",
                "discount_amount": "0",
                "scholarship_amount": "0",
                "method": self.cash.pk,
                "period_label": "សីហា 2026",
            },
        )
        payment = Payment.objects.get()
        self.assertRedirects(response, payment.receipt.get_absolute_url())
        year = today.year
        self.assertEqual(payment.receipt.receipt_number, f"RCP-{year}-000001")
        self.assertEqual(payment.next_due_date, date(2026, 9, 1))

    def test_payment_form_payload_includes_suggested_next_due(self):
        response = self.client.get(reverse("billing:payment_create"))
        self.assertRedirects(response, f"{reverse('billing:payment_list')}?open=add")
        listing = self.client.get(reverse("billing:payment_list"))
        self.assertContains(listing, '"next_due": "2026-09-01"')
        self.assertContains(listing, "បង់ផ្នែកខ្លះ នៅ Due Date ដដែល")

    def test_payment_form_prefills_next_due_from_enrollment(self):
        response = self.client.get(
            reverse("billing:payment_create"),
            {"enrollment": self.enrollment.pk},
        )
        self.assertRedirects(
            response,
            f"{reverse('billing:payment_list')}?open=add&enrollment={self.enrollment.pk}",
        )
        listing = self.client.get(
            reverse("billing:payment_list"),
            {"open": "add", "enrollment": self.enrollment.pk},
        )
        self.assertContains(listing, 'name="next_due_date"')
        self.assertContains(listing, 'value="2026-09-01"')

    def test_payment_list_has_serial_and_collect_button(self):
        self._pay()
        response = self.client.get(reverse("billing:payment_list"))
        self.assertContains(response, "ល.រ")
        self.assertContains(response, "ទទួលបង់ប្រាក់")
        self.assertContains(response, "data-add-open")
        self.assertContains(response, 'data-modal="form-modal"')
        self.assertContains(response, "data-combobox")
        self.assertContains(response, "វាយស្វែងរកតាម ID ឈ្មោះ ឬថ្នាក់")
        self.assertContains(response, "RCP-")

    def test_viewing_receipt_opens_popup_on_list(self):
        payment = self._pay()
        response = self.client.get(payment.receipt.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-modal="receipt-modal"')
        self.assertContains(response, 'data-open-modal="receipt"')
        self.assertContains(response, "បង្កាន់ដៃបង់ថ្លៃសិក្សា")
        self.assertContains(response, payment.receipt.receipt_number)
        self.assertContains(response, "សុខា")
        self.assertContains(response, "ហត្ថលេខាអ្នកទទួលប្រាក់")
        self.assertContains(response, "data-receipt-print")
        self.assertNotContains(response, "/print/")
        self.assertIn("/payments/", payment.receipt.get_absolute_url())

    def test_print_url_opens_popup_instead_of_separate_page(self):
        payment = self._pay()
        response = self.client.get(reverse("billing:receipt_print", args=[payment.receipt.pk]))
        self.assertRedirects(response, f"{payment.receipt.get_absolute_url()}&print=1")

    def test_old_receipt_url_redirects_to_popup(self):
        payment = self._pay()
        response = self.client.get(reverse("billing:receipt_detail", args=[payment.receipt.pk]))
        self.assertRedirects(response, payment.receipt.get_absolute_url())

    def test_receipt_list_redirects_to_payments(self):
        payment = self._pay()
        response = self.client.get(reverse("billing:receipt_list"), {"view": payment.receipt.pk})
        self.assertRedirects(
            response,
            f"{reverse('billing:payment_list')}?view={payment.receipt.pk}",
        )

    def test_sidebar_keeps_payments_without_receipts_item(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, reverse("billing:payment_list"))
        self.assertContains(response, "ការបង់ប្រាក់")
        self.assertNotContains(response, reverse("billing:receipt_list"))

    def test_dashboard_shows_revenue(self):
        self._pay()
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "$30.00")
        self.assertContains(response, "ទទួលបង់ប្រាក់")
        self.assertNotContains(response, "cursor-not-allowed")

    def test_refund_keeps_original_and_full_amount(self):
        original_due = self.enrollment.next_due_date
        payment = self._pay()
        receipt = payment.receipt
        refund = refund_payment(
            payment,
            method=self.cash,
            reason="ឈប់រៀន",
            user=self.user,
        )
        payment.refresh_from_db()
        receipt.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(receipt.status, Receipt.Status.ISSUED)
        self.assertEqual(refund.amount, payment.total_amount)
        self.assertEqual(refund.currency, payment.currency)
        self.assertEqual(self.enrollment.next_due_date, original_due)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())
        self.assertTrue(Receipt.objects.filter(pk=receipt.pk).exists())
        self.assertTrue(Refund.objects.filter(pk=refund.pk).exists())

    def test_cannot_refund_twice_or_partial(self):
        payment = self._pay()
        refund_payment(payment, method=self.cash, reason="ឈប់រៀន", user=self.user)
        with self.assertRaises(ValidationError):
            refund_payment(payment, method=self.cash, reason="ម្តងទៀត", user=self.user)

    def test_cannot_void_refunded_or_refund_voided(self):
        payment = self._pay()
        void_payment(payment, user=self.user, reason="បញ្ចូលខុស")
        with self.assertRaises(ValidationError):
            refund_payment(payment, method=self.cash, reason="សង", user=self.user)
        other = self._pay()
        refund_payment(other, method=self.cash, reason="ឈប់រៀន", user=self.user)
        with self.assertRaises(ValidationError):
            void_payment(other, user=self.user)

    def test_revenue_nets_refunds(self):
        today = timezone.localdate()
        payment = self._pay()
        self.assertEqual(revenue_on(today, "USD"), Decimal("30.00"))
        refund_payment(payment, method=self.cash, reason="ឈប់រៀន", refunded_on=today, user=self.user)
        self.assertEqual(revenue_on(today, "USD"), Decimal("0.00"))

    def test_refund_cannot_be_deleted(self):
        payment = self._pay()
        refund = refund_payment(payment, method=self.cash, reason="ឈប់រៀន", user=self.user)
        with self.assertRaises(ValidationError):
            refund.delete()
        self.assertTrue(Refund.objects.filter(pk=refund.pk).exists())

    def test_collect_and_refund_write_audit(self):
        payment = self._pay()
        self.assertTrue(
            AuditEvent.objects.filter(action=AuditEvent.Action.PAYMENT_COLLECTED, object_id=str(payment.pk)).exists()
        )
        refund_payment(payment, method=self.cash, reason="ឈប់រៀន", user=self.user)
        self.assertTrue(AuditEvent.objects.filter(action=AuditEvent.Action.PAYMENT_REFUNDED).exists())

    def test_payment_list_has_refund_action(self):
        self._pay()
        response = self.client.get(reverse("billing:payment_list"))
        self.assertContains(response, "សងប្រាក់")
        self.assertContains(response, 'data-modal="refund-modal"')
        self.assertContains(response, "បានសងប្រាក់")

    def test_refund_view_creates_record(self):
        payment = self._pay()
        response = self.client.post(
            reverse("billing:payment_refund", args=[payment.pk]),
            {
                "method": self.cash.pk,
                "refunded_on": timezone.localdate().isoformat(),
                "reason": "ឈប់រៀន",
            },
        )
        self.assertRedirects(response, reverse("billing:payment_list"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(payment.receipt.status, Receipt.Status.ISSUED)

