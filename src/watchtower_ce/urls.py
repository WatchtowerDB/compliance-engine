from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularSwaggerView

from watchtower_ce.apps.users.views import (
    HybridTokenObtainPairView,
    HybridTokenRefreshView,
)

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("docs/", SpectacularSwaggerView.as_view(), name="docs"),
    path("auth/", HybridTokenObtainPairView.as_view(), name="authtoken"),
    path("auth/refresh/", HybridTokenRefreshView.as_view(), name="authtoken-refresh"),
    path("api/", include("watchtower_ce.apps.urls")),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
