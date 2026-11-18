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

    def test_editing_vehicle_keeps_its_plate_valid(self):
        vehicle = Vehicle.objects.create(owner=self.driver, plate_number="ABC-123")
        form = VehicleForm(
            {"plate_number": "abc-123", "brand_model": "Updated Model", "color": "Red"},
            instance=vehicle,
            owner=self.driver,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_vehicle_rejects_another_vehicle_plate(self):
        vehicle = Vehicle.objects.create(owner=self.driver, plate_number="ABC-123")
        Vehicle.objects.create(owner=self.driver, plate_number="XYZ-789")
        form = VehicleForm(
            {"plate_number": "xyz-789", "brand_model": "", "color": ""},
            instance=vehicle,
            owner=self.driver,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("plate_number", form.errors)


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

    def test_driver_can_edit_their_own_vehicle(self):
        vehicle = Vehicle.objects.create(
            owner=self.driver,
            plate_number="OLD-123",
            brand_model="Old Model",
            color="Blue",
        )
        self.client.force_login(self.driver)

        response = self.client.post(
            reverse("vehicles:edit", args=[vehicle.pk]),
            {
                "plate_number": " new-123 ",
                "brand_model": "New Model",
                "color": "Red",
            },
        )

        self.assertRedirects(response, reverse("vehicles:list"))
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.owner, self.driver)
        self.assertEqual(vehicle.plate_number, "NEW-123")
        self.assertEqual(vehicle.brand_model, "New Model")
        self.assertEqual(vehicle.color, "Red")

    def test_driver_cannot_edit_another_drivers_vehicle(self):
        vehicle = Vehicle.objects.create(
            owner=self.other_driver,
            plate_number="OTHER-123",
        )
        self.client.force_login(self.driver)

        response = self.client.get(reverse("vehicles:edit", args=[vehicle.pk]))

        self.assertEqual(response.status_code, 404)

    def test_driver_can_view_delete_confirmation_without_deleting_vehicle(self):
        vehicle = Vehicle.objects.create(owner=self.driver, plate_number="DEL-123")
        self.client.force_login(self.driver)

        response = self.client.get(reverse("vehicles:delete", args=[vehicle.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete vehicle?")
        self.assertTrue(Vehicle.objects.filter(pk=vehicle.pk).exists())

    def test_driver_can_delete_their_own_vehicle(self):
        vehicle = Vehicle.objects.create(owner=self.driver, plate_number="DEL-123")
        self.client.force_login(self.driver)

        response = self.client.post(reverse("vehicles:delete", args=[vehicle.pk]))

        self.assertRedirects(response, reverse("vehicles:list"))
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())

    def test_driver_cannot_delete_another_drivers_vehicle(self):
        vehicle = Vehicle.objects.create(
            owner=self.other_driver,
            plate_number="OTHER-123",
        )
        self.client.force_login(self.driver)

        response = self.client.post(reverse("vehicles:delete", args=[vehicle.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Vehicle.objects.filter(pk=vehicle.pk).exists())

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
        vehicle = Vehicle.objects.create(owner=self.driver, plate_number="TEST-123")
        protected_urls = (
            ("vehicles:list", []),
            ("vehicles:add", []),
            ("vehicles:edit", [vehicle.pk]),
            ("vehicles:delete", [vehicle.pk]),
        )
        for url_name, args in protected_urls:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=args))
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={reverse(url_name, args=args)}",
                )

        self.client.force_login(self.admin)
        for url_name, args in protected_urls:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=args))
                self.assertRedirects(response, reverse("accounts:admin_dashboard"))
