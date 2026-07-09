"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.adminpanel.views import (
    AdsView,
    AssistantView,
    LoanToolsContentView,
    WhatsAppConfigView,
    WhatsAppIntentView,
)

from apps.inquiries.urls import (
    expert_request_urls,
    loan_inquiry_urls,
    offer_urls,
    partnership_inquiry_urls,
    test_drive_urls,
)
from apps.inquiries.views import SellerLeadsView
from apps.users.urls import dealer_urls

api_v1 = [
    path("auth/", include("apps.users.urls")),
    path("cities/", include("apps.cities.urls")),
    path("listings/", include("apps.listings.urls")),
    path("inquiries/", include("apps.inquiries.urls")),
    path("leads/mine/", SellerLeadsView.as_view(), name="seller-leads"),
    path("test-drives/", include((test_drive_urls, "test-drives"))),
    path("offers/", include((offer_urls, "offers"))),
    path("loan-inquiries/", include((loan_inquiry_urls, "loan-inquiries"))),
    path("expert-requests/", include((expert_request_urls, "expert-requests"))),
    path(
        "partnership-inquiries/",
        include((partnership_inquiry_urls, "partnership-inquiries")),
    ),
    path("subscriptions/", include("apps.subscriptions.urls")),
    path("dealers/", include((dealer_urls, "dealers"))),
    path("admin-panel/", include("apps.adminpanel.urls")),
    path(
        "loan-tools/content/",
        LoanToolsContentView.as_view(),
        name="loan-tools-content",
    ),
    path("ads/", AdsView.as_view(), name="ads"),
    path("assistant/", AssistantView.as_view(), name="assistant"),
    path("whatsapp/config/", WhatsAppConfigView.as_view(), name="whatsapp-config"),
    path("whatsapp/intents/", WhatsAppIntentView.as_view(), name="whatsapp-intents"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
