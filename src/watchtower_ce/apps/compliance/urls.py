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
    path("model/init/", views.trigger_model_init, name="trigger-model-init"),
]
