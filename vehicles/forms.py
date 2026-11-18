from django import forms
from django.core.exceptions import ValidationError

from .models import Vehicle


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ("plate_number", "brand_model", "color")
        widgets = {
            "plate_number": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["plate_number"].help_text = (
            "Enter the plate number for your vehicle."
        )

    def clean_plate_number(self):
        plate_number = self.cleaned_data["plate_number"].strip().upper()
        duplicate_vehicles = Vehicle.objects.filter(
            owner=self.owner,
            plate_number__iexact=plate_number,
        )
        if self.instance.pk:
            duplicate_vehicles = duplicate_vehicles.exclude(pk=self.instance.pk)
        if duplicate_vehicles.exists():
            raise ValidationError(
                "You have already added a vehicle with this plate number."
            )
        return plate_number
