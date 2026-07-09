from rest_framework.routers import DefaultRouter
from .views import (
    ExpertRequestViewSet,
    InquiryViewSet,
    LoanInquiryViewSet,
    OfferViewSet,
    PartnershipInquiryViewSet,
    TestDriveBookingViewSet,
)

router = DefaultRouter()
router.register("", InquiryViewSet, basename="inquiry")

urlpatterns = router.urls

# Separate routers so they mount under different URL prefixes.
test_drive_router = DefaultRouter()
test_drive_router.register("", TestDriveBookingViewSet, basename="test-drive")

offer_router = DefaultRouter()
offer_router.register("", OfferViewSet, basename="offer")

loan_inquiry_router = DefaultRouter()
loan_inquiry_router.register("", LoanInquiryViewSet, basename="loan-inquiry")

partnership_inquiry_router = DefaultRouter()
partnership_inquiry_router.register(
    "", PartnershipInquiryViewSet, basename="partnership-inquiry"
)

expert_request_router = DefaultRouter()
expert_request_router.register("", ExpertRequestViewSet, basename="expert-request")

test_drive_urls = test_drive_router.urls
offer_urls = offer_router.urls
loan_inquiry_urls = loan_inquiry_router.urls
partnership_inquiry_urls = partnership_inquiry_router.urls
expert_request_urls = expert_request_router.urls
