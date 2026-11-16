import csv
import io
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from .forms import (
    LocationForm,
    ParkingReferenceForm,
    ParkingSessionForm,
    ParkingTimerForm,
    VehicleForm,
)
from .models import (
    FacilityType,
    ParkingFacility,
    ParkingLocation,
    ParkingReference,
    ParkingSession,
    ParkingStatus,
    ParkingTimer,
    Vehicle,
)


User = get_user_model()


class ParkingTestCase(TestCase):
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
            username="parkadmin",
            email="parkadmin@example.com",
            password="Secure-Admin-Password-481!",
        )
        self.facility = ParkingFacility.objects.create(
            name="Central Mall", facility_type=FacilityType.MALL
        )
        self.location = ParkingLocation.objects.create(
            facility=self.facility,
            floor_level="Level 2",
            zone="Blue",
            stall_number="B-12",
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.driver,
            plate_number="abc-123",
            brand_model="Example Sedan",
            color="Blue",
        )
        self.session = ParkingSession.objects.create(
            vehicle=self.vehicle,
            location=self.location,
        )

    @staticmethod
    def local_datetime(value):
        return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")


class VehicleTests(ParkingTestCase):
    def test_vehicle_plate_is_normalized_and_unique_per_owner(self):
        self.assertEqual(self.vehicle.plate_number, "ABC-123")
        form = VehicleForm(
            {
                "plate_number": " abc-123 ",
                "brand_model": "Another car",
                "color": "",
            },
            owner=self.driver,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("plate_number", form.errors)

    def test_different_owners_can_register_the_same_plate(self):
        form = VehicleForm(
            {"plate_number": "ABC-123", "brand_model": "", "color": ""},
            owner=self.other_driver,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_driver_can_create_update_view_and_delete_vehicle(self):
        self.client.force_login(self.driver)
        create = self.client.post(
            reverse("parking:vehicle_create"),
            {
                "plate_number": "XYZ 789",
                "brand_model": "Compact",
                "color": "White",
            },
        )
        self.assertEqual(create.status_code, 302)
        vehicle = Vehicle.objects.get(owner=self.driver, plate_number="XYZ 789")
        vehicle_session = ParkingSession.objects.create(
            vehicle=vehicle, location=self.location
        )
        detail = self.client.get(reverse("parking:vehicle_detail", args=[vehicle.pk]))
        self.assertContains(detail, "XYZ 789")
        update = self.client.post(
            reverse("parking:vehicle_update", args=[vehicle.pk]),
            {"plate_number": "XYZ 789", "brand_model": "Updated", "color": "Silver"},
        )
        self.assertRedirects(
            update, reverse("parking:vehicle_detail", args=[vehicle.pk])
        )
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.brand_model, "Updated")
        self.assertEqual(
            self.client.get(reverse("parking:vehicle_delete", args=[vehicle.pk])).status_code,
            200,
        )
        deleted = self.client.post(reverse("parking:vehicle_delete", args=[vehicle.pk]))
        self.assertRedirects(deleted, reverse("parking:vehicle_list"))
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())
        self.assertFalse(ParkingSession.objects.filter(pk=vehicle_session.pk).exists())
        self.assertTrue(ParkingSession.objects.filter(pk=self.session.pk).exists())

    def test_driver_cannot_view_or_delete_another_drivers_vehicle(self):
        self.client.force_login(self.other_driver)
        self.assertEqual(
            self.client.get(
                reverse("parking:vehicle_detail", args=[self.vehicle.pk])
            ).status_code,
            404,
        )
        response = self.client.post(
            reverse("parking:vehicle_delete", args=[self.vehicle.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

    def test_vehicle_list_only_shows_current_users_vehicles(self):
        Vehicle.objects.create(owner=self.other_driver, plate_number="OTHER-1")
        self.client.force_login(self.driver)
        response = self.client.get(reverse("parking:vehicle_list"))
        self.assertContains(response, "ABC-123")
        self.assertNotContains(response, "OTHER-1")


class FacilityAndLocationTests(ParkingTestCase):
    def test_facility_name_and_spot_are_unique(self):
        duplicate_facility = ParkingFacility.objects.filter(
            name__iexact="central mall"
        )
        self.assertTrue(duplicate_facility.exists())
        duplicate_spot = LocationForm(
            {
                "facility": self.facility.pk,
                "floor_level": "level 2",
                "zone": "blue",
                "stall_number": "b-12",
            }
        )
        self.assertFalse(duplicate_spot.is_valid())
        self.assertIn("stall_number", duplicate_spot.errors)

    def test_only_administrator_can_create_shared_facilities_and_spots(self):
        self.client.force_login(self.driver)
        forbidden_facility = self.client.get(reverse("parking:facility_create"))
        forbidden_location = self.client.get(reverse("parking:location_create"))
        self.assertEqual(forbidden_facility.status_code, 302)
        self.assertEqual(forbidden_location.status_code, 302)

        self.client.force_login(self.admin)
        facility_response = self.client.post(
            reverse("parking:facility_create"),
            {"name": "University Garage", "facility_type": FacilityType.SCHOOL},
        )
        self.assertEqual(facility_response.status_code, 302)
        facility = ParkingFacility.objects.get(name="University Garage")
        location_response = self.client.post(
            reverse("parking:location_create"),
            {
                "facility": facility.pk,
                "floor_level": "B1",
                "zone": "Green",
                "stall_number": "17",
            },
        )
        self.assertEqual(location_response.status_code, 302)
        self.assertTrue(
            ParkingLocation.objects.filter(
                facility=facility,
                floor_level="B1",
                zone="Green",
                stall_number="17",
            ).exists()
        )

    def test_facility_deletion_is_blocked_when_location_is_in_use(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("parking:facility_delete", args=[self.facility.pk])
        )
        self.assertRedirects(
            response, reverse("parking:facility_detail", args=[self.facility.pk])
        )
        self.assertTrue(ParkingFacility.objects.filter(pk=self.facility.pk).exists())
        self.assertTrue(ParkingLocation.objects.filter(pk=self.location.pk).exists())

    def test_location_deletion_is_blocked_when_used_by_session(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("parking:location_delete", args=[self.location.pk])
        )
        self.assertRedirects(response, reverse("parking:location_list"))
        self.assertTrue(ParkingLocation.objects.filter(pk=self.location.pk).exists())

    def test_driver_can_browse_shared_facilities_and_locations(self):
        self.client.force_login(self.driver)
        facility_response = self.client.get(reverse("parking:facility_list"))
        location_response = self.client.get(reverse("parking:location_list"))
        detail_response = self.client.get(
            reverse("parking:location_detail", args=[self.location.pk])
        )
        self.assertContains(facility_response, "Central Mall")
        self.assertContains(location_response, "B-12")
        self.assertContains(detail_response, "Level 2")


class ParkingSessionTests(ParkingTestCase):
    def test_driver_can_create_filter_complete_and_delete_session(self):
        self.client.force_login(self.driver)
        another_session = self.client.post(
            reverse("parking:session_create"),
            {
                "vehicle": self.vehicle.pk,
                "location": self.location.pk,
                "parked_at": self.local_datetime(timezone.now() - timedelta(days=2)),
                "status": ParkingStatus.COMPLETED,
            },
        )
        self.assertEqual(another_session.status_code, 302)
        completed_session = ParkingSession.objects.get(
            vehicle=self.vehicle, status=ParkingStatus.COMPLETED
        )
        detail = self.client.get(
            reverse("parking:session_detail", args=[completed_session.pk])
        )
        self.assertContains(detail, "Central Mall")

        filtered = self.client.get(
            reverse("parking:session_list"),
            {"q": "B-12", "status": "COMPLETED", "vehicle": self.vehicle.pk},
        )
        self.assertEqual(len(filtered.context["page_obj"].object_list), 1)

        complete = self.client.post(
            reverse("parking:session_complete", args=[self.session.pk])
        )
        self.assertRedirects(
            complete, reverse("parking:session_detail", args=[self.session.pk])
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, ParkingStatus.COMPLETED)

        self.client.get(reverse("parking:session_delete", args=[self.session.pk]))
        deleted = self.client.post(
            reverse("parking:session_delete", args=[self.session.pk])
        )
        self.assertRedirects(deleted, reverse("parking:session_list"))
        self.assertFalse(ParkingSession.objects.filter(pk=self.session.pk).exists())

    def test_driver_cannot_select_another_drivers_vehicle(self):
        other_vehicle = Vehicle.objects.create(
            owner=self.other_driver, plate_number="PRIVATE-1"
        )
        form = ParkingSessionForm(
            {
                "vehicle": other_vehicle.pk,
                "location": self.location.pk,
                "parked_at": self.local_datetime(timezone.now()),
                "status": ParkingStatus.COMPLETED,
            },
            owner=self.driver,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("vehicle", form.errors)

    def test_driver_cannot_view_update_complete_or_delete_another_drivers_session(self):
        other_vehicle = Vehicle.objects.create(
            owner=self.other_driver, plate_number="PRIVATE-2"
        )
        other_session = ParkingSession.objects.create(
            vehicle=other_vehicle, location=self.location
        )
        self.client.force_login(self.driver)
        routes = [
            ("parking:session_detail", "get"),
            ("parking:session_update", "get"),
            ("parking:session_delete", "post"),
            ("parking:session_complete", "post"),
        ]
        for route_name, method in routes:
            with self.subTest(route=route_name):
                response = getattr(self.client, method)(
                    reverse(route_name, args=[other_session.pk])
                )
                self.assertEqual(response.status_code, 404)
        self.assertEqual(other_session.status, ParkingStatus.ACTIVE)

    def test_administrator_cannot_view_a_drivers_private_parking_session(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("parking:session_detail", args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_is_redirected_from_parking_pages(self):
        response = self.client.get(reverse("parking:session_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_vehicle_cannot_have_a_second_active_session(self):
        form = ParkingSessionForm(
            {
                "vehicle": self.vehicle.pk,
                "location": self.location.pk,
                "parked_at": self.local_datetime(timezone.now()),
                "status": ParkingStatus.ACTIVE,
            },
            owner=self.driver,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("vehicle", form.errors)

    def test_csv_report_is_scoped_to_the_current_driver(self):
        other_vehicle = Vehicle.objects.create(
            owner=self.other_driver, plate_number="PRIVATE-3"
        )
        ParkingSession.objects.create(
            vehicle=other_vehicle, location=self.location
        )
        self.client.force_login(self.driver)
        response = self.client.get(reverse("parking:report_csv"))
        self.assertEqual(response["Content-Type"], "text/csv")
        report = list(csv.reader(io.StringIO(response.content.decode())))
        self.assertIn("ABC-123", report[1])
        self.assertNotIn("PRIVATE-3", response.content.decode())

    def test_csv_export_escapes_spreadsheet_formulas(self):
        self.vehicle.plate_number = "=1+2"
        self.vehicle.save()
        self.client.force_login(self.driver)
        response = self.client.get(reverse("parking:report_csv"))
        self.assertIn("'=1+2", response.content.decode())


class ReferenceAndTimerTests(ParkingTestCase):
    def setUp(self):
        super().setUp()
        self.temp_media = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.temp_media.cleanup)

    @staticmethod
    def image_upload(name="reference.png"):
        from PIL import Image

        output = io.BytesIO()
        Image.new("RGB", (4, 4), "blue").save(output, format="PNG")
        return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")

    def test_reference_requires_a_photo_or_note(self):
        form = ParkingReferenceForm(data={"note": ""})
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_driver_can_add_view_and_delete_note_reference(self):
        self.client.force_login(self.driver)
        response = self.client.post(
            reverse("parking:reference_create", args=[self.session.pk]),
            {"note": "Near the blue elevator."},
        )
        self.assertRedirects(
            response, reverse("parking:session_detail", args=[self.session.pk])
        )
        reference = ParkingReference.objects.get(session=self.session)
        detail = self.client.get(
            reverse("parking:session_detail", args=[self.session.pk])
        )
        self.assertContains(detail, "Near the blue elevator.")
        deleted = self.client.post(
            reverse("parking:reference_delete", args=[reference.pk])
        )
        self.assertRedirects(
            deleted, reverse("parking:session_detail", args=[self.session.pk])
        )
        self.assertFalse(ParkingReference.objects.filter(pk=reference.pk).exists())

    def test_photo_is_validated_and_served_only_to_owner(self):
        self.client.force_login(self.driver)
        response = self.client.post(
            reverse("parking:reference_create", args=[self.session.pk]),
            {"photo": self.image_upload(), "note": ""},
        )
        self.assertEqual(response.status_code, 302)
        reference = ParkingReference.objects.get(session=self.session)
        photo = self.client.get(reverse("parking:reference_photo", args=[reference.pk]))
        self.assertEqual(photo.status_code, 200)
        self.assertEqual(photo["Content-Type"], "image/png")
        self.assertIn("private", photo["Cache-Control"])

        self.client.force_login(self.other_driver)
        forbidden = self.client.get(
            reverse("parking:reference_photo", args=[reference.pk])
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_timer_requires_expiration_after_start(self):
        start = timezone.now()
        form = ParkingTimerForm(
            {
                "start_time": self.local_datetime(start),
                "expiration_time": self.local_datetime(start - timedelta(minutes=1)),
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("expiration_time", form.errors)

    def test_driver_can_create_update_and_delete_timer(self):
        self.client.force_login(self.driver)
        start = timezone.now() + timedelta(minutes=1)
        expiration = start + timedelta(minutes=30)
        response = self.client.post(
            reverse("parking:timer_update", args=[self.session.pk]),
            {
                "start_time": self.local_datetime(start),
                "expiration_time": self.local_datetime(expiration),
            },
        )
        self.assertRedirects(
            response, reverse("parking:session_detail", args=[self.session.pk])
        )
        timer = ParkingTimer.objects.get(session=self.session)
        detail = self.client.get(
            reverse("parking:session_detail", args=[self.session.pk])
        )
        self.assertContains(detail, "Time remaining")
        updated_expiration = expiration + timedelta(minutes=15)
        update = self.client.post(
            reverse("parking:timer_update", args=[self.session.pk]),
            {
                "start_time": self.local_datetime(start),
                "expiration_time": self.local_datetime(updated_expiration),
            },
        )
        self.assertEqual(update.status_code, 302)
        timer.refresh_from_db()
        self.assertAlmostEqual(
            timer.expiration_time.timestamp(),
            updated_expiration.timestamp(),
            delta=60,
        )
        deleted = self.client.post(
            reverse("parking:timer_delete", args=[self.session.pk])
        )
        self.assertRedirects(
            deleted, reverse("parking:session_detail", args=[self.session.pk])
        )
        self.assertFalse(ParkingTimer.objects.filter(pk=timer.pk).exists())

    def test_driver_cannot_manage_another_drivers_timer(self):
        other_vehicle = Vehicle.objects.create(
            owner=self.other_driver, plate_number="PRIVATE-4"
        )
        other_session = ParkingSession.objects.create(
            vehicle=other_vehicle, location=self.location
        )
        self.client.force_login(self.driver)
        response = self.client.post(
            reverse("parking:timer_update", args=[other_session.pk]),
            {
                "start_time": self.local_datetime(timezone.now()),
                "expiration_time": self.local_datetime(
                    timezone.now() + timedelta(hours=1)
                ),
            },
        )
        self.assertEqual(response.status_code, 404)


class ReportTests(ParkingTestCase):
    def test_report_contains_database_driven_summary_and_month_grouping(self):
        self.client.force_login(self.driver)
        response = self.client.get(reverse("parking:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["total"], 1)
        self.assertEqual(response.context["summary"]["active"], 1)
        self.assertEqual(response.context["summary"]["completed"], 0)
        self.assertEqual(len(response.context["per_vehicle"]), 1)
        self.assertEqual(len(response.context["per_facility"]), 1)
        self.assertEqual(len(response.context["per_month"]), 1)

    def test_report_filters_only_the_current_drivers_records(self):
        other_vehicle = Vehicle.objects.create(
            owner=self.other_driver, plate_number="PRIVATE-5"
        )
        ParkingSession.objects.create(
            vehicle=other_vehicle, location=self.location
        )
        self.client.force_login(self.driver)
        response = self.client.get(
            reverse("parking:reports"),
            {"date_from": "2020-01-01", "date_to": "2020-01-31"},
        )
        self.assertEqual(response.context["summary"]["total"], 0)
