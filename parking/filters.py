from django import forms

from .models import ParkingFacility, ParkingStatus, Vehicle


class ParkingSessionFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search", max_length=100)
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *ParkingStatus.choices],
    )
    vehicle = forms.ModelChoiceField(
        required=False,
        queryset=Vehicle.objects.none(),
        empty_label="All vehicles",
    )
    facility = forms.ModelChoiceField(
        required=False,
        queryset=ParkingFacility.objects.all(),
        empty_label="All facilities",
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="From",
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="To",
    )
    floor = forms.CharField(required=False, max_length=20, label="Floor / level")
    zone = forms.CharField(required=False, max_length=30)

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.filter(owner=owner)
        for field in self.fields.values():
            if isinstance(field, forms.ChoiceField):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get("date_from"), cleaned_data.get("date_to")
        if start and end and end < start:
            self.add_error("date_to", "The end date must be on or after the start date.")
        return cleaned_data
