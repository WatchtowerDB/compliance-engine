from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from .apps.users.views import (
    HybridTokenObtainPairView,
    HybridTokenRefreshView,
)

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/", include("watchtower_ce.apps.urls")),
    path("auth/", HybridTokenObtainPairView.as_view(), name="authtoken"),
    path("auth/refresh/", HybridTokenRefreshView.as_view(), name="authtoken-refresh"),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# A "dev" vs "prod" check would also work here, but DEBUG is sufficient for now
if settings.DEBUG:
    from drf_spectacular.views import SpectacularRedocView, SpectacularSwaggerView

    urlpatterns += [
        path("docs/redoc/", SpectacularRedocView.as_view(), name="redoc-docs"),
        path("docs/swagger/", SpectacularSwaggerView.as_view(), name="swagger-docs"),
    ]
