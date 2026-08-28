from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

handler403 = "django.views.defaults.permission_denied"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("users/", include("apps.accounts.user_urls")),
    path("students/", include("apps.students.urls")),
    path("", include("apps.academics.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.billing.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

