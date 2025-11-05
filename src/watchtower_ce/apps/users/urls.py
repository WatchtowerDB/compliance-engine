from django.urls import URLPattern, URLResolver
from rest_framework import routers

from . import views

router: routers.SimpleRouter = routers.SimpleRouter()
router.register("", views.UserViewSet)

urlpatterns: list[URLPattern | URLResolver] = router.urls
