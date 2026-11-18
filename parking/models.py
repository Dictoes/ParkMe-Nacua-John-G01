from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


class FacilityType(models.TextChoices):
    MALL = "MALL", "Mall"
    SCHOOL = "SCHOOL", "School"
    OFFICE = "OFFICE", "Office"
    PARKING_BUILDING = "PARKING_BUILDING", "Parking building"
    OTHER = "OTHER", "Other"


class ParkingStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"


class Vehicle(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    plate_number = models.CharField(max_length=15)
    brand_model = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["plate_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "plate_number"],
                name="unique_vehicle_plate_per_owner",
            ),
        ]

    def save(self, *args, **kwargs):
        self.plate_number = self.plate_number.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plate_number} ({self.brand_model or 'Vehicle'})"


class ParkingFacility(models.Model):
    name = models.CharField(max_length=150, unique=True)
    facility_type = models.CharField(max_length=20, choices=FacilityType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=Q(facility_type__in=FacilityType.values),
                name="valid_parking_facility_type",
            ),
            models.UniqueConstraint(
                Lower("name"),
                name="unique_facility_name_case_insensitive",
            ),
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ParkingLocation(models.Model):
    facility = models.ForeignKey(
        ParkingFacility,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    floor_level = models.CharField(max_length=20)
    zone = models.CharField(max_length=30)
    stall_number = models.CharField(max_length=20)

    class Meta:
        ordering = ["facility__name", "floor_level", "zone", "stall_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "floor_level", "zone", "stall_number"],
                name="unique_spot_per_facility",
            ),
        ]

    def save(self, *args, **kwargs):
        self.floor_level = self.floor_level.strip()
        self.zone = self.zone.strip()
        self.stall_number = self.stall_number.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.facility} · {self.floor_level} · {self.zone} · {self.stall_number}"


class ParkingSession(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="parking_sessions",
    )
    location = models.ForeignKey(
        ParkingLocation,
        on_delete=models.PROTECT,
        related_name="parking_sessions",
    )
    parked_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10,
        choices=ParkingStatus.choices,
        default=ParkingStatus.ACTIVE,
    )

    class Meta:
        ordering = ["-parked_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=ParkingStatus.values),
                name="valid_parking_session_status",
            ),
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(status=ParkingStatus.ACTIVE),
                name="unique_active_session_per_vehicle",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "parked_at"], name="park_status_time_idx"),
            models.Index(fields=["vehicle", "parked_at"], name="park_vehicle_time_idx"),
        ]

    @property
    def owner(self):
        return self.vehicle.owner

    def clean(self):
        super().clean()
        if (
            self.status == ParkingStatus.ACTIVE
            and self.vehicle_id
            and self.location_id
        ):
            active_elsewhere = ParkingSession.objects.filter(
                vehicle_id=self.vehicle_id,
                status=ParkingStatus.ACTIVE,
            )
            if self.pk:
                active_elsewhere = active_elsewhere.exclude(pk=self.pk)
            if active_elsewhere.exists():
                raise ValidationError(
                    {"vehicle": "This vehicle already has an active parking session."}
                )

    def __str__(self):
        return f"{self.vehicle.plate_number} at {self.location}"


class ParkingReference(models.Model):
    session = models.ForeignKey(
        ParkingSession,
        on_delete=models.CASCADE,
        related_name="references",
    )
    photo = models.ImageField(
        upload_to="parking-references/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )
    note = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.CheckConstraint(
                check=~Q(photo="") | ~Q(note=""),
                name="parking_reference_has_photo_or_note",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.photo and not self.note.strip():
            raise ValidationError("Add a photo, a note, or both for this reference.")

    def __str__(self):
        return f"Reference for session {self.session_id}"
