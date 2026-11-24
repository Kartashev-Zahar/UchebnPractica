from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from prokat_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", views.VhodView.as_view(), name="login"),
    path("accounts/password_change/", views.SmenaParolyaView.as_view(), name="password_change"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("prokat_app.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "prokat_app.views.error_403"
handler404 = "prokat_app.views.error_404"
handler500 = "prokat_app.views.error_500"

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
