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
    path("model/init/", views.trigger_model_init, name="trigger-model-init"),
    path(
        "analytics/schema-iterations/",
        views.schema_iteration_chart,
        name="analytics-schema-iterations",
    ),
]
