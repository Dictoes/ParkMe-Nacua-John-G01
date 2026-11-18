from django.conf import settings
from django.db import models


class Vehicle(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    plate_number = models.CharField(max_length=15)
    brand_model = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["plate_number", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "plate_number"],
                name="vehicles_owner_plate_unique",
            ),
        ]

    def save(self, *args, **kwargs):
        self.plate_number = self.plate_number.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plate_number} ({self.brand_model or 'Vehicle'})"
