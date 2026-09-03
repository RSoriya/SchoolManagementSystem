from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.academics.models import Course, Enrollment
from apps.core.constants import format_money
from apps.core.models import PaymentMethod

from .services import PAYABLE_STATUSES, compute_payment_total, monthly_schedule, payable_enrollments, period_balance

INPUT_ATTRS = {"class": "form-input"}


class DataSelect(forms.Select):
    def __init__(self, *args, extra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra = extra or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        key = str(getattr(value, "value", value) or "")
        for attr_name, attr_value in self.extra.get(key, {}).items():
            option["attrs"][attr_name] = attr_value
        return option


class EnrollmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        student = obj.student
        name = student.name_kh
        if student.name_en:
            name = f"{student.name_kh} ({student.name_en})"
        return f"{student.student_id} · {name} · {obj.course_class.name}"


class PaymentForm(forms.Form):
    enrollment = EnrollmentChoiceField(
        label="សិស្ស / ថ្នាក់",
        queryset=Enrollment.objects.none(),
        widget=forms.Select(
            attrs={
                **INPUT_ATTRS,
                "data-combobox": "1",
                "data-combobox-placeholder": "វាយស្វែងរក ID ឈ្មោះ ឬថ្នាក់",
            }
        ),
    )
    paid_on = forms.DateField(
        label="ថ្ងៃបង់",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    tuition_amount = forms.DecimalField(
        label="ថ្លៃសិក្សា",
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01", "min": "0"}),
    )
    registration_fee = forms.DecimalField(
        label="ថ្លៃចុះឈ្មោះ",
        min_value=0,
        decimal_places=2,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01", "min": "0"}),
    )
    late_fee = forms.DecimalField(
        label="ថ្លៃយឺត (ដោយដៃ)",
        min_value=0,
        decimal_places=2,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01", "min": "0"}),
    )
    discount_amount = forms.DecimalField(
        label="បញ្ចុះតម្លៃ",
        min_value=0,
        decimal_places=2,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01", "min": "0"}),
    )
    scholarship_amount = forms.DecimalField(
        label="អាហារូបករ",
        min_value=0,
        decimal_places=2,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01", "min": "0"}),
    )
    method = forms.ModelChoiceField(
        label="វិធីបង់ប្រាក់",
        queryset=PaymentMethod.objects.none(),
        widget=DataSelect(attrs=INPUT_ATTRS),
    )
    transaction_reference = forms.CharField(
        label="លេខយោងប្រតិបត្តិការ",
        required=False,
        max_length=80,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
    )
    period_label = forms.CharField(
        label="រយៈពេល",
        required=False,
        max_length=80,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
    )
    period_start = forms.DateField(
        label="ចាប់ផ្ដើម",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    period_end = forms.DateField(
        label="បញ្ចប់",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    next_due_date = forms.DateField(
        label="Due Date បន្ទាប់",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        help_text="វគ្គប្រចាំខែ៖ បង់ពេញរួច ប្រព័ន្ធដាក់ Due Date បន្ទាប់ស្វ័យ (+១ ខែ)។ បង់ផ្នែកខ្លះ នៅ Due Date ដដែល។",
    )
    note = forms.CharField(
        label="កំណត់ចំណាំ",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        enrollments = payable_enrollments()
        self.fields["enrollment"].queryset = enrollments
        self.fields["enrollment"].empty_label = "ជ្រើសសិស្ស និងថ្នាក់"
        methods = PaymentMethod.objects.filter(is_active=True)
        self.fields["method"].queryset = methods
        self.fields["method"].empty_label = "ជ្រើសវិធីបង់ប្រាក់"
        self.fields["method"].widget.extra = {
            str(method.pk): {
                "data-requires-reference": "1" if method.requires_reference else "0",
            }
            for method in methods
        }
        for name in ("paid_on", "period_start", "period_end", "next_due_date"):
            self.fields[name].input_formats = ["%Y-%m-%d"]

        if not self.is_bound:
            enrollment = None
            enrollment_id = self.initial.get("enrollment")
            if enrollment_id:
                enrollment = enrollments.filter(pk=enrollment_id).first()
            if enrollment:
                course = enrollment.course_class.course
                balance = period_balance(
                    enrollment,
                    paid_on=self.initial.get("paid_on") or timezone.localdate(),
                )
                self.initial.setdefault("tuition_amount", balance["remaining"])
                if course.fee_type == Course.FeeType.MONTHLY:
                    suggestion = monthly_schedule(
                        enrollment,
                        self.initial.get("paid_on") or timezone.localdate(),
                    )
                    if balance["remaining"] < balance["fee"] and enrollment.next_due_date:
                        self.initial.setdefault("next_due_date", enrollment.next_due_date)
                    else:
                        self.initial.setdefault("next_due_date", suggestion["next_due_date"])
                    self.initial.setdefault("period_start", suggestion["period_start"])
                    self.initial.setdefault("period_end", suggestion["period_end"])
                    self.initial.setdefault("period_label", suggestion["period_label"])

    def clean(self):
        cleaned = super().clean()
        enrollment = cleaned.get("enrollment")
        method = cleaned.get("method")
        reference = (cleaned.get("transaction_reference") or "").strip()
        if enrollment and enrollment.status not in PAYABLE_STATUSES:
            self.add_error("enrollment", "អាចទទួលបង់បានតែសិស្សដែលកំពុងរៀន ឬផ្អាក។")
        if method and method.requires_reference and not reference:
            self.add_error("transaction_reference", "សូមបំពេញលេខយោងប្រតិបត្តិការ។")
        if method and not method.requires_reference:
            cleaned["transaction_reference"] = ""

        tuition = cleaned.get("tuition_amount")
        try:
            cleaned["total_amount"] = compute_payment_total(
                tuition,
                cleaned.get("registration_fee"),
                cleaned.get("late_fee"),
                cleaned.get("discount_amount"),
                cleaned.get("scholarship_amount"),
            )
        except ValidationError as exc:
            self.add_error(None, exc)

        if enrollment:
            balance = period_balance(
                enrollment,
                paid_on=cleaned.get("paid_on"),
                period_start=cleaned.get("period_start"),
            )
            tuition = cleaned.get("tuition_amount")
            if tuition is not None and tuition > balance["remaining"]:
                self.add_error(
                    "tuition_amount",
                    f"ថ្លៃសិក្សាលើសចំនួននៅជំពាក់ ({format_money(balance['remaining'], enrollment.course_class.course.currency)})។",
                )

        if enrollment and enrollment.course_class.course.fee_type == Course.FeeType.MONTHLY:
            suggestion = monthly_schedule(enrollment, cleaned.get("paid_on"))
            if not cleaned.get("next_due_date"):
                cleaned["next_due_date"] = suggestion["next_due_date"]
            if not cleaned.get("period_start"):
                cleaned["period_start"] = suggestion["period_start"]
            if not cleaned.get("period_end"):
                cleaned["period_end"] = suggestion["period_end"]
            if not (cleaned.get("period_label") or "").strip():
                cleaned["period_label"] = suggestion["period_label"]

        period_start = cleaned.get("period_start")
        period_end = cleaned.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error("period_end", "ថ្ងៃបញ្ចប់ត្រូវនៅក្រោយថ្ងៃចាប់ផ្ដើម។")
        return cleaned


class RefundForm(forms.Form):
    method = forms.ModelChoiceField(
        label="វិធីសងប្រាក់",
        queryset=PaymentMethod.objects.none(),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )
    refunded_on = forms.DateField(
        label="ថ្ងៃសង",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    reason = forms.CharField(
        label="មូលហេតុ",
        max_length=255,
        widget=forms.TextInput(attrs={**INPUT_ATTRS, "placeholder": "មូលហេតុសងប្រាក់ពេញ"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        methods = PaymentMethod.objects.filter(is_active=True)
        self.fields["method"].queryset = methods
        self.fields["method"].empty_label = "ជ្រើសវិធីសងប្រាក់"
        self.fields["refunded_on"].input_formats = ["%Y-%m-%d"]
        if not self.is_bound:
            self.initial.setdefault("refunded_on", timezone.localdate())
