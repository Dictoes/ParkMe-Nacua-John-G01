from django import forms
from django.core.exceptions import ValidationError

from .models import (
    ParkingFacility,
    ParkingLocation,
    ParkingReference,
    ParkingSession,
    Vehicle,
)


class BootstrapFormMixin:
    def style_fields(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class VehicleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ("plate_number", "brand_model", "color")
        widgets = {
            "plate_number": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)
        self.style_fields()

    def clean_plate_number(self):
        plate = self.cleaned_data["plate_number"].strip().upper()
        existing = Vehicle.objects.filter(owner=self.owner, plate_number__iexact=plate)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError("You have already registered this plate number.")
        return plate


class FacilityForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParkingFacility
        fields = ("name", "facility_type")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        existing = ParkingFacility.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError("A facility with this name already exists.")
        return name


class LocationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParkingLocation
        fields = ("facility", "floor_level", "zone", "stall_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()

    def clean(self):
        cleaned_data = super().clean()
        facility = cleaned_data.get("facility")
        floor = cleaned_data.get("floor_level")
        zone = cleaned_data.get("zone")
        stall = cleaned_data.get("stall_number")
        if facility and floor and zone and stall:
            duplicate = ParkingLocation.objects.filter(
                facility=facility,
                floor_level__iexact=floor.strip(),
                zone__iexact=zone.strip(),
                stall_number__iexact=stall.strip(),
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error("stall_number", "This spot is already listed for this facility.")
        return cleaned_data


class ParkingSessionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParkingSession
        fields = ("vehicle", "location", "parked_at", "status")
        widgets = {
            "parked_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
        }

    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.filter(owner=owner)
        self.fields["location"].queryset = ParkingLocation.objects.select_related("facility")
        self.fields["location"].label_from_instance = lambda location: str(location)
        self.fields["parked_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S%z"]
        self.fields["parked_at"].widget.attrs["class"] = "form-control"
        self.fields["vehicle"].widget.attrs["class"] = "form-select"
        self.fields["location"].widget.attrs["class"] = "form-select"
        self.fields["status"].widget.attrs["class"] = "form-select"

    def clean(self):
        cleaned_data = super().clean()
        vehicle = cleaned_data.get("vehicle")
        status = cleaned_data.get("status")
        if vehicle and vehicle.owner_id != self.owner.pk:
            self.add_error("vehicle", "Choose one of your own vehicles.")
        if vehicle and status == "ACTIVE":
            active_elsewhere = ParkingSession.objects.filter(
                vehicle=vehicle,
                status="ACTIVE",
            )
            if self.instance.pk:
                active_elsewhere = active_elsewhere.exclude(pk=self.instance.pk)
            if active_elsewhere.exists():
                self.add_error("vehicle", "This vehicle already has an active parking session.")
        return cleaned_data


class ParkingReferenceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParkingReference
        fields = ("photo", "note")
        widgets = {
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
            "note": forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["photo"].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        photo = cleaned_data.get("photo")
        note = cleaned_data.get("note", "").strip()
        if not photo and not note:
            raise ValidationError("Add a photo, a note, or both for this reference.")
        if photo and photo.size > 5 * 1024 * 1024:
            self.add_error("photo", "Image files must be 5 MB or smaller.")
        return cleaned_data
