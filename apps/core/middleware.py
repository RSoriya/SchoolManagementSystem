from django.utils.translation import get_language

from .language import translate_html


class TranslateHtmlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not (get_language() or "").startswith("en"):
            return response
        if request.path.startswith("/admin/"):
            return response
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type or not hasattr(response, "content"):
            return response
        html = response.content.decode(response.charset or "utf-8")
        head = html[:1200].lower()
        if "<html" in head and "data-no-i18n" in head:
            return response
        response.content = translate_html(html).encode(response.charset or "utf-8")
        if "Content-Length" in response:
            del response["Content-Length"]
        return response
