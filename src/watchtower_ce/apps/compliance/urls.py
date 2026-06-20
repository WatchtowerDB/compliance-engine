from django.urls import URLPattern, URLResolver, path
from rest_framework import routers

from . import views

router: routers.SimpleRouter = routers.SimpleRouter()
router.register("frameworks", views.ComplianceFrameworkViewSet)
router.register("clientdb", views.ClientDBViewSet)
router.register("clientdbschema", views.ClientDBSchemaViewSet)
router.register("assertions", views.ComplianceAssertionViewSet)
router.register("checks", views.ComplianceCheckViewSet)

urlpatterns: list[URLPattern | URLResolver] = [
    *router.urls,
    path(
        "checks/<int:check_id>/stream/",
        views.stream_check_updates,
        name="stream-check-updates",
    ),
    path(
        "analytics/schema-iterations/",
        views.schema_iteration_chart,
        name="analytics-schema-iterations",
    ),
    path("model/status/", views.model_status, name="model-status"),
]
