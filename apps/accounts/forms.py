from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.core.exceptions import ValidationError

from .models import User
from .roles import ADMIN_GROUP_NAME, ROLE_CHOICES, assign_role, user_role
from .services import can_change_role

INPUT_ATTRS = {"class": "form-input"}


class AdminAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label="ឈ្មោះអ្នកប្រើប្រាស់",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "បញ្ចូលឈ្មោះអ្នកប្រើប្រាស់",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="ពាក្យសម្ងាត់",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "បញ្ចូលពាក្យសម្ងាត់",
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label="ចងចាំខ្ញុំ",
        required=False,
        widget=forms.CheckboxInput(),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_active:
            raise ValidationError("គណនីនេះត្រូវបានផ្អាក។", code="inactive")


class AdminUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="ពាក្យសម្ងាត់",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={**INPUT_ATTRS, "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="បញ្ជាក់ពាក្យសម្ងាត់",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={**INPUT_ATTRS, "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["username", "full_name_kh", "phone_number", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs=INPUT_ATTRS),
            "full_name_kh": forms.TextInput(attrs=INPUT_ATTRS),
            "phone_number": forms.TextInput(attrs=INPUT_ATTRS),
            "email": forms.EmailInput(attrs=INPUT_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"] = forms.ChoiceField(
            label="តួនាទី",
            choices=ROLE_CHOICES,
            required=False,
            widget=forms.Select(attrs=INPUT_ATTRS),
        )
        self.fields["full_name_kh"].required = True
        if self.instance.pk:
            self.fields["role"].initial = user_role(self.instance)
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True
            self.fields["is_active"].initial = True
            self.fields["role"].initial = ADMIN_GROUP_NAME

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1") or ""
        password2 = cleaned.get("password2") or ""
        if password1 or password2 or not self.instance.pk:
            if password1 != password2:
                self.add_error("password2", "ពាក្យសម្ងាត់មិនដូចគ្នា។")
            elif password1:
                try:
                    password_validation.validate_password(password1, self.instance)
                except ValidationError as exc:
                    self.add_error("password1", exc)
        role = cleaned.get("role") or (
            user_role(self.instance) if self.instance.pk else ADMIN_GROUP_NAME
        )
        cleaned["role"] = role
        if self.instance.pk and not can_change_role(self.instance, role):
            self.add_error("role", "មិនអាចដកតួនាទី Admin ចុងក្រោយបានទេ។")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        elif not user.pk:
            raise ValidationError("សូមបំពេញពាក្យសម្ងាត់។")
        if commit:
            user.save()
            assign_role(user, self.cleaned_data["role"])
        return user
