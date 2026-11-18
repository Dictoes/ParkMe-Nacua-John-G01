from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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


class VehiclePageTests(TestCase):
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
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Secure-Admin-Password-481!",
        )

    def test_driver_can_add_vehicle_and_view_it_in_their_list(self):
        self.client.force_login(self.driver)

        response = self.client.post(
            reverse("vehicles:add"),
            {
                "plate_number": " abC-123 ",
                "brand_model": "Example Sedan",
                "color": "Blue",
            },
        )

        self.assertRedirects(response, reverse("vehicles:list"))
        vehicle = Vehicle.objects.get(owner=self.driver)
        self.assertEqual(vehicle.plate_number, "ABC-123")
        self.assertEqual(vehicle.brand_model, "Example Sedan")
        self.assertEqual(vehicle.color, "Blue")
        self.assertContains(self.client.get(reverse("vehicles:list")), "ABC-123")

    def test_driver_dashboard_links_to_add_vehicle_and_shows_vehicle_count(self):
        self.client.force_login(self.driver)

        response = self.client.get(reverse("accounts:driver_dashboard"))

        self.assertContains(response, reverse("vehicles:add"))
        self.assertContains(response, "Registered vehicles:")
        self.assertEqual(response.context["vehicle_count"], 0)

    def test_vehicle_list_only_shows_current_drivers_vehicles(self):
        Vehicle.objects.create(owner=self.driver, plate_number="OWN-123")
        Vehicle.objects.create(owner=self.other_driver, plate_number="OTHER-123")
        self.client.force_login(self.driver)

        response = self.client.get(reverse("vehicles:list"))

        self.assertContains(response, "OWN-123")
        self.assertNotContains(response, "OTHER-123")

    def test_vehicle_pages_require_driver_role(self):
        for url_name in ("vehicles:list", "vehicles:add"):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={reverse(url_name)}",
                )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("vehicles:list"))
        self.assertRedirects(response, reverse("accounts:admin_dashboard"))
