from django import forms
from django.forms.widgets import CheckboxInput, FileInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import PaymentMethod, SchoolSettings


INPUT_ATTRS = {"class": "form-input"}


class LogoInput(forms.ClearableFileInput):
    clear_checkbox_label = "លុបរូបបច្ចុប្បន្ន"

    def render(self, name, value, attrs=None, renderer=None):
        file_html = FileInput(attrs=self.build_attrs(self.attrs, attrs)).render(
            name, value, attrs, renderer
        )
        if self.is_initial(value):
            preview = format_html(
                '<img src="{}" alt="" class="size-20 shrink-0 rounded-2xl border border-slate-200 object-cover">',
                value.url,
            )
            checkbox_name = self.clear_checkbox_name(name)
            checkbox_id = self.clear_checkbox_id(checkbox_name)
            clear = format_html(
                '<label class="mt-3 inline-flex items-center gap-2 text-sm text-slate-500" for="{}">{} {}</label>',
                checkbox_id,
                mark_safe(
                    CheckboxInput().render(
                        checkbox_name, False, attrs={"id": checkbox_id}
                    )
                ),
                self.clear_checkbox_label,
            )
        else:
            preview = mark_safe(
                '<div class="flex size-20 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-2xl font-bold text-brand-700">S</div>'
            )
            clear = ""
        return format_html(
            '<div class="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">{}<div class="min-w-0 flex-1">{}{}</div></div>',
            preview,
            mark_safe(file_html),
            mark_safe(clear) if clear else "",
        )


class SchoolSettingsForm(forms.ModelForm):
    telegram_bot_token = forms.CharField(
        label="Telegram Bot Token",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                **INPUT_ATTRS,
                "placeholder": "ទុកចោលដើម្បីរក្សាទុកតម្លៃចាស់",
                "autocomplete": "new-password",
            },
            render_value=False,
        ),
        help_text="ផ្ញើទៅ Admin chat តែប៉ុណ្ណោះ។ ទុកចោលប្រសិនបើមិនចង់ផ្លាស់ប្ដូរ។",
    )

    class Meta:
        model = SchoolSettings
        fields = [
            "school_name",
            "address",
            "phone",
            "logo",
            "reminder_days_before_due",
            "overdue_alert_daily",
            "telegram_bot_token",
            "telegram_admin_chat_id",
        ]
        widgets = {
            "school_name": forms.TextInput(attrs=INPUT_ATTRS),
            "address": forms.TextInput(attrs=INPUT_ATTRS),
            "phone": forms.TextInput(attrs=INPUT_ATTRS),
            "logo": LogoInput(attrs={"accept": "image/*", "class": "settings-file"}),
            "reminder_days_before_due": forms.NumberInput(attrs={**INPUT_ATTRS, "min": "1", "max": "30"}),
            "telegram_admin_chat_id": forms.TextInput(attrs=INPUT_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._existing_token = ""
        if self.instance and self.instance.pk:
            self._existing_token = self.instance.telegram_bot_token or ""
        self.fields["telegram_bot_token"].initial = ""
        self.token_configured = bool(self._existing_token)

    def save(self, commit=True):
        instance = super().save(commit=False)
        token = (self.cleaned_data.get("telegram_bot_token") or "").strip()
        instance.telegram_bot_token = token or self._existing_token
        if commit:
            instance.save()
        return instance


class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ["name", "code", "requires_reference", "is_active", "sort_order"]
        widgets = {
            "name": forms.TextInput(attrs=INPUT_ATTRS),
            "code": forms.TextInput(attrs={**INPUT_ATTRS, "placeholder": "ឧ. cash"}),
            "sort_order": forms.NumberInput(attrs={**INPUT_ATTRS, "min": "0"}),
        }
        help_texts = {
            "code": "កូដខ្លីសម្រាប់ប្រព័ន្ធ។ មិនប្ដូរបន្ទាប់ពីមានការបង់។",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk:
            last = (
                PaymentMethod.objects.order_by("-sort_order")
                .values_list("sort_order", flat=True)
                .first()
            )
            self.fields["sort_order"].initial = (last or 0) + 1
            self.fields["is_active"].initial = True

