import uuid
from django.db import models


class City(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    state = models.CharField(max_length=80)
    popular = models.BooleanField(default=False)
    car_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-popular", "name")
        verbose_name_plural = "Cities"

    def __str__(self) -> str:
        return f"{self.name}, {self.state}"
