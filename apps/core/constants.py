WEEKDAY_CHOICES = [
    (0, "ច័ន្ទ"),
    (1, "អង្គារ"),
    (2, "ពុធ"),
    (3, "ព្រហស្បតិ៍"),
    (4, "សុក្រ"),
    (5, "សៅរ៍"),
    (6, "អាទិត្យ"),
]

WEEKDAY_LABELS = {value: label for value, label in WEEKDAY_CHOICES}

CURRENCY_CHOICES = [
    ("USD", "USD"),
    ("KHR", "KHR"),
]

KHMER_MONTHS = {
    1: "មករា",
    2: "កុម្ភៈ",
    3: "មីនា",
    4: "មេសា",
    5: "ឧសភា",
    6: "មិថុនា",
    7: "កក្កដា",
    8: "សីហា",
    9: "កញ្ញា",
    10: "តុលា",
    11: "វិច្ឆិកា",
    12: "ធ្នូ",
}

DEFAULT_PAYMENT_METHODS = [
    {"name": "Cash", "code": "cash", "requires_reference": False, "sort_order": 1},
    {"name": "ABA", "code": "aba", "requires_reference": True, "sort_order": 2},
    {"name": "ACLEDA", "code": "acleda", "requires_reference": True, "sort_order": 3},
    {"name": "Wing", "code": "wing", "requires_reference": True, "sort_order": 4},
    {"name": "KHQR", "code": "khqr", "requires_reference": True, "sort_order": 5},
]


def format_weekdays(days):
    labels = []
    for day in days or []:
        try:
            labels.append(WEEKDAY_LABELS[int(day)])
        except (TypeError, ValueError, KeyError):
            continue
    return " · ".join(labels)


def format_money(amount, currency):
    from decimal import Decimal, ROUND_HALF_UP

    value = Decimal(amount or 0)
    if currency == "KHR":
        quantized = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"៛{quantized:,.0f}"
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${quantized:,.2f}"
