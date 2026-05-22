from rest_framework import permissions, viewsets
from .models import City
from .serializers import CitySerializer


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/cities/  — public list of cities."""
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filterset_fields = ("popular",)
    search_fields = ("name", "state")
    ordering_fields = ("name", "car_count")
