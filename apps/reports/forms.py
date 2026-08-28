from django import forms

from apps.academics.models import Course, CourseClass
from apps.billing.models import Payment
from apps.core.constants import CURRENCY_CHOICES
from apps.core.models import PaymentMethod

INPUT_ATTRS = {"class": "form-input"}

REPORT_KINDS = {
    "revenue": "ចំណូល",
    "paid": "សិស្សបានបង់",
    "unpaid": "សិស្សមិនទាន់បង់",
    "overdue": "សិស្សហួស Due Date",
    "refunds": "ការសងប្រាក់",
    "attendance": "វត្តមាន",
}

SNAPSHOT_KINDS = {"unpaid", "overdue"}


class ReportFilterForm(forms.Form):
    date_from = forms.DateField(
        label="ពីថ្ងៃ",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    date_to = forms.DateField(
        label="ដល់ថ្ងៃ",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    course = forms.ModelChoiceField(
        label="វគ្គសិក្សា",
        required=False,
        queryset=Course.objects.none(),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )
    course_class = forms.ModelChoiceField(
        label="ថ្នាក់រៀន",
        required=False,
        queryset=CourseClass.objects.none(),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )
    currency = forms.ChoiceField(
        label="រូបិយប័ណ្ណ",
        required=False,
        choices=[("", "គ្រប់រូបិយប័ណ្ណ")] + list(CURRENCY_CHOICES),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )
    method = forms.ModelChoiceField(
        label="វិធីបង់",
        required=False,
        queryset=PaymentMethod.objects.none(),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )
    status = forms.ChoiceField(
        label="ស្ថានភាព",
        required=False,
        choices=[("", "គ្រប់ស្ថានភាព")] + list(Payment.Status.choices),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )

    def __init__(self, *args, kind="revenue", **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = kind
        self.fields["course"].queryset = Course.objects.order_by("name")
        self.fields["course"].empty_label = "គ្រប់វគ្គ"
        classes = CourseClass.objects.select_related("course").order_by("name")
        course = None
        if self.is_bound:
            course_id = self.data.get("course")
            if course_id and str(course_id).isdigit():
                course = Course.objects.filter(pk=course_id).first()
        elif self.initial.get("course"):
            course = self.initial["course"]
        if course:
            classes = classes.filter(course=course)
        self.fields["course_class"].queryset = classes
        self.fields["course_class"].empty_label = "គ្រប់ថ្នាក់"
        self.fields["method"].queryset = PaymentMethod.objects.all()
        self.fields["method"].empty_label = "គ្រប់វិធីបង់"
        if kind in SNAPSHOT_KINDS:
            self.fields.pop("date_from")
            self.fields.pop("date_to")
            self.fields.pop("method")
            self.fields.pop("status")
            self.fields.pop("currency")
        elif kind == "paid":
            self.fields.pop("status")
        elif kind == "refunds":
            self.fields.pop("status")
        elif kind == "attendance":
            self.fields.pop("method")
            self.fields.pop("status")
            self.fields.pop("currency")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("date_from")
        end = cleaned.get("date_to")
        if start and end and end < start:
            self.add_error("date_to", "ថ្ងៃបញ្ចប់ត្រូវនៅក្រោយថ្ងៃចាប់ផ្ដើម។")
        return cleaned
