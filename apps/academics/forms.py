from django import forms
from django.db.models import Q

from apps.accounts.roles import instructor_queryset
from apps.core.constants import WEEKDAY_CHOICES
from apps.students.models import Student

from .models import Assessment, Course, CourseClass, Enrollment

INPUT_ATTRS = {"class": "form-input"}


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "name_kh", "description", "fee_type", "default_fee", "currency", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs=INPUT_ATTRS),
            "name_kh": forms.TextInput(attrs=INPUT_ATTRS),
            "description": forms.Textarea(attrs={**INPUT_ATTRS, "rows": 3}),
            "fee_type": forms.Select(attrs=INPUT_ATTRS),
            "default_fee": forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01"}),
            "currency": forms.Select(attrs=INPUT_ATTRS),
        }


class CourseClassForm(forms.ModelForm):
    study_days = forms.TypedMultipleChoiceField(
        label="ថ្ងៃសិក្សា",
        choices=WEEKDAY_CHOICES,
        coerce=int,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "study-days-list"}),
        required=True,
    )

    class Meta:
        model = CourseClass
        fields = [
            "course",
            "name",
            "instructor",
            "instructor_name",
            "start_date",
            "end_date",
            "study_days",
            "start_time",
            "end_time",
            "is_active",
        ]
        widgets = {
            "course": forms.Select(attrs=INPUT_ATTRS),
            "name": forms.TextInput(attrs=INPUT_ATTRS),
            "instructor": forms.Select(attrs=INPUT_ATTRS),
            "instructor_name": forms.TextInput(attrs=INPUT_ATTRS),
            "start_date": forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={**INPUT_ATTRS, "type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={**INPUT_ATTRS, "type": "time"}, format="%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Course.objects.filter(is_active=True)
        if self.instance.pk and self.instance.course_id:
            queryset = Course.objects.filter(Q(is_active=True) | Q(pk=self.instance.course_id))
        self.fields["course"].queryset = queryset.order_by("name")
        self.fields["instructor"].queryset = instructor_queryset()
        self.fields["instructor"].required = False
        self.fields["instructor"].empty_label = "— ជ្រើសគណនីគ្រូ —"
        if self.instance.pk:
            self.fields["study_days"].initial = self.instance.study_days
        for name in ("start_date", "end_date"):
            self.fields[name].input_formats = ["%Y-%m-%d"]
        for name in ("start_time", "end_time"):
            self.fields[name].input_formats = ["%H:%M", "%H:%M:%S"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.study_days = [int(day) for day in self.cleaned_data["study_days"]]
        instructor = self.cleaned_data.get("instructor")
        if instructor and not (self.cleaned_data.get("instructor_name") or "").strip():
            instance.instructor_name = (
                instructor.full_name_kh or instructor.get_full_name() or instructor.username
            )
        if commit:
            instance.save()
        return instance


class EnrollIntoClassForm(forms.Form):
    student = forms.ModelChoiceField(
        label="សិស្ស",
        queryset=Student.objects.filter(is_active=True).order_by("name_kh"),
        widget=forms.Select(
            attrs={
                **INPUT_ATTRS,
                "data-combobox": "1",
                "data-combobox-placeholder": "វាយស្វែងរក ID ឬឈ្មោះសិស្ស",
            }
        ),
    )
    next_due_date = forms.DateField(
        label="Due Date",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
    )
    note = forms.CharField(
        label="កំណត់ចំណាំ",
        required=False,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].label_from_instance = lambda obj: (
            f"{obj.student_id} · {obj.name_kh}" + (f" ({obj.name_en})" if obj.name_en else "")
        )


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ["name", "assessed_on", "max_score"]
        widgets = {
            "name": forms.TextInput(attrs={**INPUT_ATTRS, "placeholder": "ឧ. ប្រឡងកណ្ដាលវគ្គ"}),
            "assessed_on": forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "max_score": forms.NumberInput(attrs={**INPUT_ATTRS, "step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assessed_on"].input_formats = ["%Y-%m-%d"]
        self.fields["max_score"].initial = self.fields["max_score"].initial or 100
        if not self.is_bound and not self.initial.get("assessed_on"):
            from django.utils import timezone

            self.fields["assessed_on"].initial = timezone.localdate()


class TransferEnrollmentForm(forms.Form):
    course_class = forms.ModelChoiceField(
        label="ថ្នាក់ថ្មី",
        queryset=CourseClass.objects.none(),
        widget=forms.Select(attrs=INPUT_ATTRS),
    )
    note = forms.CharField(
        label="កំណត់ចំណាំ",
        required=False,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
    )

    def __init__(self, *args, enrollment=None, **kwargs):
        super().__init__(*args, **kwargs)
        taken_ids = Enrollment.objects.filter(
            student=enrollment.student,
            status=Enrollment.Status.ACTIVE,
        ).values_list("course_class_id", flat=True)
        self.fields["course_class"].queryset = (
            CourseClass.objects.filter(is_active=True)
            .exclude(pk__in=list(taken_ids) + [enrollment.course_class_id])
            .select_related("course")
            .order_by("name")
        )
