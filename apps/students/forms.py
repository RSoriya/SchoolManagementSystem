from django import forms

from .models import Student

INPUT_ATTRS = {"class": "form-input"}
GUARDIAN_RELATIONSHIP_CHOICES = [
    ("", "—"),
    ("ឪពុក", "ឪពុក"),
    ("ម្ដាយ", "ម្ដាយ"),
    ("អាណាព្យាបាល", "អាណាព្យាបាល"),
    ("ផ្សេងៗ", "ផ្សេងៗ"),
]


class StudentForm(forms.ModelForm):
    guardian_relationship = forms.ChoiceField(
        label="តំណាង",
        choices=GUARDIAN_RELATIONSHIP_CHOICES,
        required=False,
        widget=forms.Select(attrs=INPUT_ATTRS),
    )

    class Meta:
        model = Student
        fields = [
            "photo",
            "name_kh",
            "name_en",
            "gender",
            "date_of_birth",
            "phone",
            "email",
            "address",
            "guardian_name",
            "guardian_phone",
            "guardian_relationship",
            "notes",
            "is_active",
        ]
        widgets = {
            "name_kh": forms.TextInput(attrs=INPUT_ATTRS),
            "name_en": forms.TextInput(attrs=INPUT_ATTRS),
            "gender": forms.Select(attrs=INPUT_ATTRS),
            "date_of_birth": forms.DateInput(attrs={**INPUT_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "phone": forms.TextInput(attrs=INPUT_ATTRS),
            "email": forms.EmailInput(attrs=INPUT_ATTRS),
            "address": forms.TextInput(attrs=INPUT_ATTRS),
            "guardian_name": forms.TextInput(attrs=INPUT_ATTRS),
            "guardian_phone": forms.TextInput(attrs=INPUT_ATTRS),
            "notes": forms.Textarea(attrs={**INPUT_ATTRS, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_of_birth"].input_formats = ["%Y-%m-%d"]

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and getattr(photo, "size", 0) > 2 * 1024 * 1024:
            raise forms.ValidationError("រូបថតមិនត្រូវធំជាង 2MB ទេ។")
        return photo
