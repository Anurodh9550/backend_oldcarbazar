from rest_framework.routers import DefaultRouter
from .views import CityViewSet

router = DefaultRouter()
router.register("", CityViewSet, basename="city")

urlpatterns = router.urls
