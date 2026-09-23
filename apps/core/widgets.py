from django.forms.widgets import PasswordInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe

_EYE_SHOW = (
    '<svg data-password-icon="show" class="size-5" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
    '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/>'
    '<circle cx="12" cy="12" r="3"/></svg>'
)
_EYE_HIDE = (
    '<svg data-password-icon="hide" class="hidden size-5" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
    '<path d="M3 3l18 18"/><path d="M10.6 10.6A3 3 0 0012 15a3 3 0 002.4-4.8"/>'
    '<path d="M9.9 5.2A11 11 0 0112 5c6.5 0 10 7 10 7a18 18 0 01-4.2 5.1"/>'
    '<path d="M6.1 6.1A18 18 0 002 12s3.5 7 10 7a11 11 0 003.8-.7"/></svg>'
)


class PasswordToggleInput(PasswordInput):
    def render(self, name, value, attrs=None, renderer=None):
        field = super().render(name, value, attrs, renderer)
        return format_html(
            '<div class="password-field">{}'
            '<button type="button" class="password-toggle" data-password-toggle '
            'aria-label="{}" aria-pressed="false">{}{}</button></div>',
            mark_safe(field),
            "បង្ហាញពាក្យសម្ងាត់",
            mark_safe(_EYE_SHOW),
            mark_safe(_EYE_HIDE),
        )
