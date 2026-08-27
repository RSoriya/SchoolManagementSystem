from django import forms
from django.db.models import Q

from apps.core.constants import WEEKDAY_CHOICES
from apps.students.models import Student

from .models import Course, CourseClass, Enrollment

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
        if self.instance.pk:
            self.fields["study_days"].initial = self.instance.study_days
        for name in ("start_date", "end_date"):
            self.fields[name].input_formats = ["%Y-%m-%d"]
        for name in ("start_time", "end_time"):
            self.fields[name].input_formats = ["%H:%M", "%H:%M:%S"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.study_days = [int(day) for day in self.cleaned_data["study_days"]]
        if commit:
            instance.save()
        return instance


class EnrollStudentForm(forms.Form):
    course_class = forms.ModelChoiceField(
        label="ថ្នាក់រៀន",
        queryset=CourseClass.objects.none(),
        widget=forms.Select(attrs=INPUT_ATTRS),
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

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        taken_ids = Enrollment.objects.filter(
            student=student,
            status=Enrollment.Status.ACTIVE,
        ).values_list("course_class_id", flat=True)
        self.fields["course_class"].queryset = (
            CourseClass.objects.filter(is_active=True)
            .exclude(pk__in=taken_ids)
            .select_related("course")
            .order_by("name")
        )
        self.fields["next_due_date"].input_formats = ["%Y-%m-%d"]


class EnrollIntoClassForm(forms.Form):
    student = forms.ModelChoiceField(
        label="សិស្ស",
        queryset=Student.objects.filter(is_active=True).order_by("name_kh"),
        widget=forms.Select(attrs=INPUT_ATTRS),
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
