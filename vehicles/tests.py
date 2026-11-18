from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from django.test import TestCase

from .forms import VehicleForm
from .models import Vehicle


User = get_user_model()


class VehicleDataTests(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver",
            email="driver@example.com",
            password="Secure-Driver-Password-481!",
        )
        self.other_driver = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="Secure-Other-Password-481!",
        )

    def test_vehicle_normalizes_plate_and_stores_optional_details(self):
        vehicle = Vehicle.objects.create(
            owner=self.driver,
            plate_number="  abc-123 ",
            brand_model="Example Sedan",
            color="Blue",
        )

        self.assertEqual(vehicle.plate_number, "ABC-123")
        self.assertEqual(vehicle.brand_model, "Example Sedan")
        self.assertEqual(vehicle.color, "Blue")

    def test_plate_number_is_required_but_optional_details_may_be_blank(self):
        form = VehicleForm(
            {"plate_number": "", "brand_model": "", "color": ""},
            owner=self.driver,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("plate_number", form.errors)

        form = VehicleForm(
            {"plate_number": "XYZ-789", "brand_model": "", "color": ""},
            owner=self.driver,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_same_owner_cannot_add_duplicate_plate_in_different_case(self):
        Vehicle.objects.create(owner=self.driver, plate_number="ABC-123")
        form = VehicleForm(
            {"plate_number": "abc-123", "brand_model": "", "color": ""},
            owner=self.driver,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("plate_number", form.errors)

    def test_different_owners_can_register_the_same_plate(self):
        Vehicle.objects.create(owner=self.driver, plate_number="ABC-123")
        form = VehicleForm(
            {"plate_number": "ABC-123", "brand_model": "", "color": ""},
            owner=self.other_driver,
        )

        self.assertTrue(form.is_valid(), form.errors)
