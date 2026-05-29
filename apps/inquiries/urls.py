from rest_framework.routers import DefaultRouter
from .views import InquiryViewSet, OfferViewSet, TestDriveBookingViewSet

router = DefaultRouter()
router.register("", InquiryViewSet, basename="inquiry")

urlpatterns = router.urls

# Separate routers so they mount under different URL prefixes.
test_drive_router = DefaultRouter()
test_drive_router.register("", TestDriveBookingViewSet, basename="test-drive")

offer_router = DefaultRouter()
offer_router.register("", OfferViewSet, basename="offer")

test_drive_urls = test_drive_router.urls
offer_urls = offer_router.urls
