"""django-filter filterset for marketplace search."""
import django_filters as df
from .models import Listing


class ListingFilter(df.FilterSet):
    city = df.CharFilter(field_name="location", lookup_expr="iexact")
    brand = df.CharFilter(lookup_expr="iexact")
    fuel = df.CharFilter(lookup_expr="iexact")
    transmission = df.CharFilter(lookup_expr="iexact")
    body_type = df.CharFilter(field_name="body_type", lookup_expr="iexact")
    ownership = df.CharFilter(lookup_expr="iexact")
    featured = df.BooleanFilter()
    moderation = df.CharFilter()
    status = df.CharFilter()

    # price in lakhs from query string
    min_price = df.NumberFilter(method="filter_min_price")
    max_price = df.NumberFilter(method="filter_max_price")
    max_kms = df.NumberFilter(field_name="kms", lookup_expr="lte")

    class Meta:
        model = Listing
        fields = (
            "city", "brand", "fuel", "transmission", "body_type",
            "ownership", "featured", "moderation", "status",
        )

    def filter_min_price(self, qs, name, value):
        return qs.filter(price_inr__gte=value * 100000)

    def filter_max_price(self, qs, name, value):
        return qs.filter(price_inr__lte=value * 100000)
