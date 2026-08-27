from django.core.paginator import Paginator

PER_PAGE_CHOICES = (10, 20)
DEFAULT_PER_PAGE = 20


def per_page_value(request, default=DEFAULT_PER_PAGE):
    try:
        value = int(request.GET.get("per_page", default))
    except (TypeError, ValueError):
        return default
    if value in PER_PAGE_CHOICES:
        return value
    return default


def paginate(request, items, default=DEFAULT_PER_PAGE):
    return Paginator(items, per_page_value(request, default)).get_page(request.GET.get("page"))


def extra_query(request, drop=("page",)):
    params = request.GET.copy()
    for key in drop:
        params.pop(key, None)
    encoded = params.urlencode()
    return f"&{encoded}" if encoded else ""
